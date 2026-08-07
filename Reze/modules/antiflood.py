"""
Antiflood - if the same user posts more than `limit` messages in a row
with nobody else talking in between, act on them. Tracked in memory
(per-process) rather than the database since it needs to be fast and the
state is only ever useful for a few seconds anyway.
"""
from pyrogram import Client, filters
from pyrogram.errors import RPCError
from pyrogram.types import ChatPermissions

from Reze.database.chats_db import get_chat, set_antiflood
from Reze.utils.decorators import admins_only
from Reze.utils.helpers import is_exempt, mention_md

MUTE_PERMS = ChatPermissions()
_flood_state = {}  # chat_id -> {"user_id": int, "count": int}


@Client.on_message(filters.command("antiflood") & filters.group)
@admins_only()
async def antiflood_status_cmd(client, message):
    if len(message.command) < 2:
        chat = await get_chat(message.chat.id)
        af = chat["antiflood"]
        state = "on" if af["enabled"] else "off"
        await message.reply_text(
            f"Antiflood is **{state}** — limit **{af['limit']}** consecutive messages, action **{af['mode']}**.\n"
            f"`/antiflood <on|off>` · `/setflood <number>` · `/floodmode <ban|kick|mute>`"
        )
        return
    state = message.command[1].lower()
    if state not in ("on", "off"):
        await message.reply_text("Use `/antiflood on` or `/antiflood off`.")
        return
    await set_antiflood(message.chat.id, enabled=(state == "on"))
    await message.reply_text(f"Antiflood is now **{state}**.")


@Client.on_message(filters.command("setflood") & filters.group)
@admins_only()
async def setflood_cmd(client, message):
    if len(message.command) < 2 or not message.command[1].isdigit():
        await message.reply_text("Give me a number, e.g. `/setflood 8`.")
        return
    limit = max(2, int(message.command[1]))
    await set_antiflood(message.chat.id, limit=limit, enabled=True)
    await message.reply_text(f"Antiflood limit set to **{limit}** consecutive messages.")


@Client.on_message(filters.command("floodmode") & filters.group)
@admins_only()
async def floodmode_cmd(client, message):
    valid = ("ban", "kick", "mute")
    if len(message.command) < 2 or message.command[1].lower() not in valid:
        await message.reply_text(f"Use `/floodmode <{'|'.join(valid)}>`.")
        return
    mode = message.command[1].lower()
    await set_antiflood(message.chat.id, mode=mode)
    await message.reply_text(f"Flooders will now get: **{mode}**.")


@Client.on_message(filters.group & ~filters.service, group=3)
async def track_flood(client, message):
    if not message.from_user:
        return
    chat = await get_chat(message.chat.id)
    af = chat["antiflood"]
    if not af["enabled"]:
        return

    state = _flood_state.get(message.chat.id)
    if state and state["user_id"] == message.from_user.id:
        state["count"] += 1
    else:
        state = {"user_id": message.from_user.id, "count": 1}
        _flood_state[message.chat.id] = state

    if state["count"] <= af["limit"]:
        return

    _flood_state[message.chat.id] = {"user_id": None, "count": 0}

    if await is_exempt(client, message.chat.id, message.from_user.id):
        return

    try:
        if af["mode"] == "ban":
            await client.ban_chat_member(message.chat.id, message.from_user.id)
        elif af["mode"] == "kick":
            await client.ban_chat_member(message.chat.id, message.from_user.id)
            await client.unban_chat_member(message.chat.id, message.from_user.id)
        else:
            await client.restrict_chat_member(message.chat.id, message.from_user.id, MUTE_PERMS)
        await message.reply_text(
            f"{mention_md(message.from_user.id, message.from_user.first_name)} was flooding the chat — {af['mode']}ned. 🔥"
        )
    except RPCError:
        pass
