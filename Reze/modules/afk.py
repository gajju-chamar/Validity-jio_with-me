"""
/afk marks you away; if someone pings or replies to you while you're
AFK, Reze answers on your behalf. Clears itself the moment you post
again.
"""
import time

from pyrogram import Client, filters

from Reze.database.afk_db import set_afk, clear_afk, get_afk
from Reze.utils.helpers import extract_user, mention_md


def _ago(seconds: float) -> str:
    seconds = int(seconds)
    if seconds < 60:
        return f"{seconds}s"
    if seconds < 3600:
        return f"{seconds // 60}m"
    if seconds < 86400:
        return f"{seconds // 3600}h"
    return f"{seconds // 86400}d"


@Client.on_message(filters.command("afk"))
async def afk_cmd(client, message):
    reason = message.text.split(None, 1)[1] if len(message.command) > 1 else ""
    await set_afk(message.from_user.id, reason)
    await message.reply_text(f"Gone quiet for a bit{' — ' + reason if reason else ''}. I'll let people know. 🔥")


@Client.on_message(filters.group & filters.text & ~filters.via_bot, group=6)
async def afk_watch(client, message):
    if message.from_user:
        state = await get_afk(message.from_user.id)
        if state:
            await clear_afk(message.from_user.id)
            await message.reply_text(f"Welcome back, {message.from_user.first_name}. Missed anything? 🔥")

    target = await extract_user(client, message)
    if target and message.from_user and target.id != message.from_user.id:
        state = await get_afk(target.id)
        if state:
            ago = _ago(time.time() - state["since"])
            reason = f" — _{state['reason']}_" if state.get("reason") else ""
            await message.reply_text(f"{mention_md(target.id, target.first_name)} is AFK ({ago} ago){reason}.")
