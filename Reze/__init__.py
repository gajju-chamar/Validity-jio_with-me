import asyncio

try:
    import uvloop
    uvloop.install()
except ImportError:
    pass  # not installed (e.g. Windows) - asyncio's default loop still works fine

# Create and set the loop explicitly, here, before Client() is
# constructed below. Confirmed by direct trace: `python3 -m Reze`
# executes this entire __init__.py file - including constructing
# Client() below, which binds its Dispatcher to whatever event loop
# exists at that exact moment - BEFORE __main__.py's own top-level code
# even starts running. That's fundamental to how `python3 -m <package>`
# works (the package has to be imported before Python can even locate
# its __main__.py), not something fixable by reordering code within
# __main__.py itself. loop is exposed here so __main__.py can reuse this
# exact object instead of creating a second, mismatched one - two
# different loop objects means handler-registration tasks get scheduled
# on one loop while the bot actually runs on the other, and silently
# never execute. No errors, no crash - just total, permanent silence.
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)

from pyrogram import Client

from Reze.config import Config
from Reze.logger import LOGGER

__version__ = Config.VERSION

# Smart Plugins: every @Client.on_message / @Client.on_chat_member_updated
# handler inside Reze/modules/*.py is auto-discovered and registered here -
# no manual import list to maintain as modules are added or removed.
app = Client(
    name="Reze",
    api_id=Config.API_ID,
    api_hash=Config.API_HASH,
    bot_token=Config.BOT_TOKEN,
    in_memory=True,
    plugins=dict(root="Reze/modules"),
)

LOGGER.info("Reze core initialised.")
