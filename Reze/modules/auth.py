"""
Global access control.

Reze has two layers of authorization:

1. GLOBAL USER ALLOWLIST
   Only users listed in ALLOWED_USERS or SUDO_USERS can use the bot.

2. CHAT AUTHORIZATION
   Groups must also be authorized through APPROVED_GROUPS or the
   database-backed /authgroup system.

Therefore, in a group:

    allowed user + authorized group = Reze works
    allowed user + unauthorized group = Reze stays blocked
    unauthorized user + authorized group = Reze stays blocked
    unauthorized user + unauthorized group = Reze stays blocked

DMs:

    allowed user = full access
    unauthorized user = /start only

ALLOWED_USERS is intended for people who should have permanent access
to the entire bot.

Example environment variable:

    ALLOWED_USERS=123456789,987654321,555555555

User IDs are used instead of usernames so changing a Telegram username
doesn't break authorization.

SUDO_USERS always bypasses the global user restriction.
"""

import re

from pyrogram import Client, filters, StopPropagation
from pyrogram.enums import ChatType
from pyrogram.errors import RPCError

from Reze.config import Config
from Reze.database.auth_db import (
    approve_group,
    unapprove_group,
    is_group_approved_db,
    approve_dm_user,
    unapprove_dm_user,
    is_dm_user_approved_db,
    list_all,
)
from Reze.utils.decorators import owner_only
from Reze.utils.helpers import extract_user, mention_md


# =========================================================
# Command detection
# =========================================================

_CMD_RE = re.compile(r"^/(\w+)(?:@\w+)?")


# =========================================================
# Messages
# =========================================================

NOT_AUTH_USER_MSG = (
    "You're not on my guest list. 🌚"
)

NOT_AUTH_GROUP_MSG = (
    "This group isn't authorized. Whoever owns this bot needs to run "
    "`/authgroup` here, or add this chat's id to `APPROVED_GROUPS`. "
    "I'll stay quiet otherwise."
)

NOT_AUTH_DM_MSG = (
    "I'm limited to `/start` for you until the owner approves access."
)


# =========================================================
# Authorization helpers
# =========================================================

def is_user_allowed(user_id: int) -> bool:
    """
    Global user authorization.

    SUDO_USERS always have access.
    ALLOWED_USERS is the permanent environment allowlist.
    """

    return (
        user_id in Config.ALLOWED_USERS
        or user_id in Config.SUDO_USERS
    )


async def is_group_authorized(chat_id: int) -> bool:
    """
    Check whether a group itself is authorized.
    """

    if chat_id in Config.APPROVED_GROUPS:
        return True

    return await is_group_approved_db(chat_id)


async def is_dm_user_authorized(user_id: int) -> bool:
    """
    Legacy DM authorization.

    Global ALLOWED_USERS/SUDO_USERS always win.
    ALLOWED_DM_USERS and the DB-backed DM list are retained
    for compatibility with the existing auth system.
    """

    if is_user_allowed(user_id):
        return True

    if user_id in Config.ALLOWED_DM_USERS:
        return True

    return await is_dm_user_approved_db(user_id)


# =========================================================
# /authgroup
# =========================================================

@Client.on_message(filters.command("authgroup"))
@owner_only
async def authgroup_cmd(client, message):

    if (
        len(message.command) > 1
        and message.command[1].lstrip("-").isdigit()
    ):
        chat_id = int(message.command[1])

    elif message.chat.type != ChatType.PRIVATE:
        chat_id = message.chat.id

    else:
        await message.reply_text(
            "Run this inside the group you want to authorize, "
            "or give me its id:\n"
            "`/authgroup -100xxxxxxxxxx`"
        )
        return

    await approve_group(chat_id)

    await message.reply_text(
        f"Authorized — chat `{chat_id}` can use me now. 🔥"
    )


# =========================================================
# /deauthgroup
# =========================================================

@Client.on_message(filters.command("deauthgroup"))
@owner_only
async def deauthgroup_cmd(client, message):

    if (
        len(message.command) > 1
        and message.command[1].lstrip("-").isdigit()
    ):
        chat_id = int(message.command[1])

    elif message.chat.type != ChatType.PRIVATE:
        chat_id = message.chat.id

    else:
        await message.reply_text(
            "Give me a chat id:\n"
            "`/deauthgroup -100xxxxxxxxxx`\n"
            "or run this inside the group."
        )
        return

    if chat_id in Config.APPROVED_GROUPS:

        await message.reply_text(
            f"`{chat_id}` is authorized through the "
            "`APPROVED_GROUPS` environment variable.\n\n"
            "Remove it from Railway and redeploy to revoke it."
        )
        return

    await unapprove_group(chat_id)

    await message.reply_text(
        f"Revoked — `{chat_id}` can't use me anymore."
    )


# =========================================================
# /authuser
# =========================================================

@Client.on_message(filters.command("authuser"))
@owner_only
async def authuser_cmd(client, message):

    target = await extract_user(client, message)

    if target is None:

        await message.reply_text(
            "Reply to their message, or give me a user id:\n"
            "`/authuser 123456789`"
        )
        return

    await approve_dm_user(target.id)

    await message.reply_text(
        f"{mention_md(target.id, target.first_name)} "
        "has full DM access now. 🔥"
    )


# =========================================================
# /deauthuser
# =========================================================

@Client.on_message(filters.command("deauthuser"))
@owner_only
async def deauthuser_cmd(client, message):

    target = await extract_user(client, message)

    if target is None:

        await message.reply_text(
            "Reply to their message, or give me a user id:\n"
            "`/deauthuser 123456789`"
        )
        return

    # Global environment authorization cannot be revoked
    # using a live command.
    if target.id in Config.ALLOWED_USERS:

        await message.reply_text(
            f"`{target.id}` is authorized through the "
            "`ALLOWED_USERS` environment variable.\n\n"
            "Remove their ID from Railway and redeploy "
            "to actually revoke global access."
        )
        return

    if target.id in Config.SUDO_USERS:

        await message.reply_text(
            f"`{target.id}` is a sudo/owner user and cannot "
            "be revoked through `/deauthuser`."
        )
        return

    await unapprove_dm_user(target.id)

    await message.reply_text(
        f"Revoked DM access for "
        f"{mention_md(target.id, target.first_name)}."
    )


# =========================================================
# /authlist
# =========================================================

@Client.on_message(filters.command(["authlist", "authstatus"]))
@owner_only
async def authlist_cmd(client, message):

    doc = await list_all()

    lines = [
        "**Global allowed users**",
        "env: "
        + (
            ", ".join(
                f"`{u}`"
                for u in Config.ALLOWED_USERS
            )
            or "none"
        ),

        "sudo: "
        + (
            ", ".join(
                f"`{u}`"
                for u in Config.SUDO_USERS
            )
            or "none"
        ),

        "",

        "**Authorized groups**",
        "env: "
        + (
            ", ".join(
                f"`{g}`"
                for g in Config.APPROVED_GROUPS
            )
            or "none"
        ),

        "live: "
        + (
            ", ".join(
                f"`{g}`"
                for g in doc.get(
                    "approved_groups",
                    []
                )
            )
            or "none"
        ),

        "",

        "**Allowed DM users**",
        "env: "
        + (
            ", ".join(
                f"`{u}`"
                for u in Config.ALLOWED_DM_USERS
            )
            or "none"
        ),

        "live: "
        + (
            ", ".join(
                f"`{u}`"
                for u in doc.get(
                    "approved_dm_users",
                    []
                )
            )
            or "none"
        ),
    ]

    await message.reply_text(
        "\n".join(lines)
    )


# =========================================================
# GROUP GATE
# =========================================================

@Client.on_message(
    filters.new_chat_members,
    group=-6,
)
async def announce_if_unauthorized(
    client,
    message,
):
    """
    If Reze is added to a group that isn't authorized,
    explain why once.
    """

    if client.me.id not in [
        u.id
        for u in message.new_chat_members
    ]:
        return

    if await is_group_authorized(
        message.chat.id
    ):
        return

    try:

        await message.reply_text(
            "Thanks for the invite, but this group isn't "
            "authorized yet. I'll stay quiet here until the "
            "owner runs `/authgroup` or adds "
            f"`{message.chat.id}` to `APPROVED_GROUPS`."
        )

    except RPCError:
        pass


# =========================================================
# GLOBAL GROUP USER GATE
# =========================================================

@Client.on_message(
    filters.group,
    group=-5,
)
async def gate_group_auth(
    client,
    message,
):
    """
    Global group security gate.

    A group being authorized does NOT mean everybody inside
    it can use Reze.

    The user must be globally allowed first.
    """

    # Ignore messages without a Telegram user.
    if not message.from_user:
        return

    user_id = message.from_user.id

    # -----------------------------------------------------
    # Sudo / owner bypass
    # -----------------------------------------------------

    if user_id in Config.SUDO_USERS:
        return

    # -----------------------------------------------------
    # Global user allowlist
    # -----------------------------------------------------

    if not is_user_allowed(user_id):

        try:
            text = (
                message.text
                or message.caption
                or ""
            )

            # Only respond to commands.
            # Normal unauthorized chat stays completely silent.
            if text and _CMD_RE.match(text):

                await message.reply_text(
                    NOT_AUTH_USER_MSG
                )

        except RPCError:
            pass

        raise StopPropagation

    # -----------------------------------------------------
    # User is allowed.
    # Now check the group.
    # -----------------------------------------------------

    if await is_group_authorized(
        message.chat.id
    ):
        return

    # -----------------------------------------------------
    # Unauthorized group
    # -----------------------------------------------------

    try:

        text = (
            message.text
            or message.caption
            or ""
        )

        # Only explain when they actually use a command.
        if text and _CMD_RE.match(text):

            await message.reply_text(
                NOT_AUTH_GROUP_MSG
            )

    except RPCError:
        pass

    raise StopPropagation


# =========================================================
# PRIVATE / DM GATE
# =========================================================

@Client.on_message(
    filters.private,
    group=-5,
)
async def gate_dm_auth(
    client,
    message,
):
    """
    DM security gate.

    /start remains publicly available.

    Everything else requires global ALLOWED_USERS,
    SUDO_USERS, ALLOWED_DM_USERS, or the existing
    database-backed DM authorization.
    """

    if message.from_user is None:
        return

    user_id = message.from_user.id

    # -----------------------------------------------------
    # Sudo / owner bypass
    # -----------------------------------------------------

    if user_id in Config.SUDO_USERS:
        return

    # -----------------------------------------------------
    # Extract command
    # -----------------------------------------------------

    text = (
        message.text
        or message.caption
        or ""
    )

    match = (
        _CMD_RE.match(text)
        if text
        else None
    )

    cmd = (
        match.group(1).lower()
        if match
        else None
    )

    # -----------------------------------------------------
    # /start is always public
    # -----------------------------------------------------

    if cmd == "start":
        return

    # -----------------------------------------------------
    # Global allowlist / existing DM authorization
    # -----------------------------------------------------

    if await is_dm_user_authorized(user_id):
        return

    # -----------------------------------------------------
    # Unauthorized DM
    # -----------------------------------------------------

    if cmd:

        try:

            await message.reply_text(
                NOT_AUTH_USER_MSG
            )

        except RPCError:
            pass

    raise StopPropagation
