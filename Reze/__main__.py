import asyncio

import aiohttp
from pyrogram import idle

from Reze.config import Config
from Reze.logger import LOGGER

Config.validate()

# Reusing the exact loop object Reze/__init__.py already created and set
# (before constructing the Client) - NOT creating a new one here.
# Confirmed by direct trace: python3 -m Reze executes Reze/__init__.py
# completely, including Client() construction, before this file's own
# top-level code even starts running - so uvloop.install() and loop
# creation living here, no matter how early in this file, is always too
# late. That has to happen in __init__.py instead, which is why it's
# imported from there rather than done locally.
from Reze import app, loop as _loop
from Reze.database import ping_database
from Reze.modules._bot_commands import MENU_COMMANDS


async def _clear_webhook():
    """Defensive, not diagnostic: an active webhook makes Telegram stop
    delivering updates through any other channel, including a direct
    MTProto session like this one. Deleting it is a no-op (still returns
    success) if none was ever set, so this is always safe to run."""
    try:
        async with aiohttp.ClientSession() as session:
            url = f"https://api.telegram.org/bot{Config.BOT_TOKEN}/deleteWebhook"
            async with session.post(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                data = await resp.json()
        if data.get("ok"):
            LOGGER.info("Webhook check: cleared (or none was set).")
        else:
            LOGGER.warning("Webhook check returned: %s", data)
    except Exception as e:
        LOGGER.warning("Couldn't verify webhook state (non-fatal): %s", e)


async def _wait_for_handlers_ready(min_expected: int = 10, timeout: float = 10.0) -> int:
    """
    Real bug, confirmed by direct reproduction: pyrofork's Client.initialize()
    calls load_plugins() (which SCHEDULES handler registration as background
    tasks rather than running it immediately) and then immediately awaits
    dispatcher.start() - which, with skip_updates=True (pyrofork's own
    default), does almost no internal awaiting and can return before those
    scheduled tasks get a real chance to run. By the time app.start()
    returns, the dispatcher can still be sitting at effectively zero
    registered handlers.

    This isn't timing-sensitive in the way it sounds: once the registration
    tasks DO get a chance to run, they finish in milliseconds (verified:
    ~35ms for 125 handlers). The fix is just making sure we wait for that to
    actually happen instead of assuming app.start() already did.

    Polls until the handler count stabilizes (stops changing across
    consecutive checks) rather than guessing a fixed sleep duration, so this
    doesn't depend on how fast or slow the host environment happens to be.
    """
    deadline = _loop.time() + timeout
    last_total = -1
    stable_checks = 0

    while _loop.time() < deadline:
        total = sum(len(v) for v in app.dispatcher.groups.values())
        if total == last_total and total >= min_expected:
            stable_checks += 1
            if stable_checks >= 3:
                return total
        else:
            stable_checks = 0
        last_total = total
        await asyncio.sleep(0.02)

    LOGGER.warning(
        "Handler count never stabilized above %d within %.1fs (stuck at %d) - "
        "registration may be incomplete. This would explain total silence "
        "even though startup looks clean.",
        min_expected, timeout, last_total,
    )
    return last_total


async def _main():
    await ping_database()
    LOGGER.info("MongoDB connection OK (db=%s).", Config.DB_NAME)

    await _clear_webhook()

    LOGGER.info("Waking Reze up...")
    await app.start()

    handler_count = await _wait_for_handlers_ready()
    LOGGER.info(
        "Reze is armed and ready~ 🔥  (@%s | id=%s) - %d handlers registered across %d groups",
        app.me.username, app.me.id, handler_count, len(app.dispatcher.groups),
    )

    try:
        await app.set_bot_commands(MENU_COMMANDS)
        LOGGER.info("Command menu registered (%d commands).", len(MENU_COMMANDS))
    except Exception as e:
        LOGGER.warning("Couldn't register the command menu (non-fatal): %s", e)

    await idle()

    await app.stop()
    LOGGER.info("Reze has stood down. See you next time.")


if __name__ == "__main__":
    # Reusing the loop object Reze/__init__.py created (imported above as
    # _loop) - not creating a new one here, which would reintroduce the
    # same "two different loops" mismatch this whole setup exists to avoid.
    try:
        _loop.run_until_complete(_main())
    finally:
        _loop.close()

