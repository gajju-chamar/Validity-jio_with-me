"""
Global access control - two layers, checked together:

1. Groups: the bot only operates in groups the owner has authorized.
   Anywhere else, every command gets a plain "not authorized" reply and
   nothing else runs - no locks, no filters, no passive chat trigger,
   nothing. `/authgroup` approves the current group instantly (stored in
   the DB); APPROVED_GROUPS in the environment is the persistent list
   that survives restarts without a live command.

2. DMs: anyone can hit /start, but every other command needs approval.
   `/authuser` (owner-only) grants it instantly; ALLOWED_DM_USERS in the
   environment is the persistent equivalent.

A chat/user is authorized if it's in EITHER the env list or the live
DB list - env vars for "people I already trust", live commands for
"someone just added me somewhere and I want it working right now."

This module's gate handlers run in the earliest handler group of any
module in this bot (-5, -6) specifically so nothing else - including
disable.py's own gate - gets a chance to run first.
"""
import re

from pyrogram import Client, filters, StopPropagation
from pyrogram.enums import ChatType
from pyrogram.errors import RPCError

from Reze.config import Config
from Reze.database.auth_db import (
    approve_group, unapprove_group, is_group_approved_db,
    approve_dm_user, unapprove_dm_user, is_dm_user_approved_db, list_all,
)
from Reze.utils.decorators import owner_only
from Reze.utils.helpers import extract_user, mention_md

_CMD_RE = re.compile(r"^/(\w+)(?:@\w+)?")

NOT_AUTH_GROUP_MSG = (
    "This group isn't authorized. Whoever owns this bot needs to run `/authgroup` in "
    "here, or add this chat's id to `APPROVED_GROUPS`. I'll stay quiet otherwise."
)
NOT_AUTH_DM_MSG = (
    "I'm limited to `/start` for you until the owner approves full access — ask them "
    "to run `/authuser` on you, or add your id to `ALLOWED_DM_USERS`."
)


async def is_group_authorized(chat_id: int) -> bool:
    if chat_id in Config.APPROVED_GROUPS:
        return True
    return await is_group_approved_db(chat_id)


async def is_dm_user_authorized(user_id: int) -> bool:
    if user_id in Config.ALLOWED_DM_USERS or user_id in Config.SUDO_USERS:
        return True
    return await is_dm_user_approved_db(user_id)


# ---------------------------------------------------------------- commands
@Client.on_message(filters.command("authgroup"))
@owner_only
async def authgroup_cmd(client, message):
    if len(message.command) > 1 and message.command[1].lstrip("-").isdigit():
        chat_id = int(message.command[1])
    elif message.chat.type != ChatType.PRIVATE:
        chat_id = message.chat.id
    else:
        await message.reply_text(
            "Run this inside the group you want to authorize, or give me its id: `/authgroup -100xxxxxxxxxx`."
        )
        return
    await approve_group(chat_id)
    await message.reply_text(f"Authorized — chat `{chat_id}` can use me now. 🔥")


@Client.on_message(filters.command("deauthgroup"))
@owner_only
async def deauthgroup_cmd(client, message):
    if len(message.command) > 1 and message.command[1].lstrip("-").isdigit():
        chat_id = int(message.command[1])
    elif message.chat.type != ChatType.PRIVATE:
        chat_id = message.chat.id
    else:
        await message.reply_text("Give me a chat id: `/deauthgroup -100xxxxxxxxxx`, or run this inside the group.")
        return
    if chat_id in Config.APPROVED_GROUPS:
        await message.reply_text(
            f"`{chat_id}` is authorized via the `APPROVED_GROUPS` env var, not the live list — "
            f"remove it there and redeploy to actually revoke it."
        )
        return
    await unapprove_group(chat_id)
    await message.reply_text(f"Revoked — `{chat_id}` can't use me anymore.")


@Client.on_message(filters.command("authuser"))
@owner_only
async def authuser_cmd(client, message):
    target = await extract_user(client, message)
    if target is None:
        await message.reply_text("Reply to their message, or give me a user id: `/authuser 123456789`.")
        return
    await approve_dm_user(target.id)
    await message.reply_text(f"{mention_md(target.id, target.first_name)} has full DM access now. 🔥")


@Client.on_message(filters.command("deauthuser"))
@owner_only
async def deauthuser_cmd(client, message):
    target = await extract_user(client, message)
    if target is None:
        await message.reply_text("Reply to their message, or give me a user id: `/deauthuser 123456789`.")
        return
    if target.id in Config.ALLOWED_DM_USERS:
        await message.reply_text(
            f"`{target.id}` is authorized via the `ALLOWED_DM_USERS` env var, not the live list — "
            f"remove it there and redeploy to actually revoke it."
        )
        return
    await unapprove_dm_user(target.id)
    await message.reply_text(f"Revoked DM access for {mention_md(target.id, target.first_name)}.")


@Client.on_message(filters.command(["authlist", "authstatus"]))
@owner_only
async def authlist_cmd(client, message):
    doc = await list_all()
    lines = [
        "**Authorized groups**",
        "env: " + (", ".join(f"`{g}`" for g in Config.APPROVED_GROUPS) or "none"),
        "live: " + (", ".join(f"`{g}`" for g in doc.get("approved_groups", [])) or "none"),
        "",
        "**Allowed DM users**",
        "env: " + (", ".join(f"`{u}`" for u in Config.ALLOWED_DM_USERS) or "none"),
        "live: " + (", ".join(f"`{u}`" for u in doc.get("approved_dm_users", [])) or "none"),
    ]
    await message.reply_text("\n".join(lines))


# ---------------------------------------------------------------- gates
@Client.on_message(filters.new_chat_members, group=-6)
async def announce_if_unauthorized(client, message):
    """If Reze herself was just added to an unapproved group, say so
    once instead of sitting silently forever with no explanation."""
    if client.me.id not in [u.id for u in message.new_chat_members]:
        return
    if await is_group_authorized(message.chat.id):
        return
    try:
        await message.reply_text(
            "Thanks for the invite — but this group isn't authorized yet. I'll stay quiet "
            f"here until the owner runs `/authgroup` or adds `{message.chat.id}` to `APPROVED_GROUPS`."
        )
    except RPCError:
        pass


@Client.on_message(filters.group, group=-5)
async def gate_group_auth(client, message):
    if message.from_user and message.from_user.id in Config.SUDO_USERS:
        return
    if await is_group_authorized(message.chat.id):
        return

    text = message.text or message.caption
    if text and _CMD_RE.match(text):
        try:
            await message.reply_text(NOT_AUTH_GROUP_MSG)
        except RPCError:
            pass
    raise StopPropagation


@Client.on_message(filters.private, group=-5)
async def gate_dm_auth(client, message):
    if message.from_user is None or message.from_user.id in Config.SUDO_USERS:
        return

    text = message.text or message.caption
    m = _CMD_RE.match(text) if text else None
    cmd = m.group(1).lower() if m else None

    if cmd == "start":
        return  # the one thing that always works, unapproved or not

    if await is_dm_user_authorized(message.from_user.id):
        return

    if cmd:
        try:
            await message.reply_text(NOT_AUTH_DM_MSG)
        except RPCError:
            pass
    raise StopPropagation
