import random
import time

from pyrogram import Client, filters
from pyrogram.enums import ChatMembersFilter

from Reze.utils.helpers import mention_md

_couple_cache = {}  # chat_id -> (date_str, (user1, user2))


@Client.on_message(filters.command("couple") & filters.group)
async def couple_cmd(client, message):
    today = time.strftime("%Y-%m-%d")
    cached = _couple_cache.get(message.chat.id)
    if cached and cached[0] == today:
        u1, u2 = cached[1]
        await message.reply_text(f"Today's couple is already set: {mention_md(*u1)} 💞 {mention_md(*u2)}")
        return

    members = []
    async for m in client.get_chat_members(message.chat.id, filter=ChatMembersFilter.RECENT):
        if m.user and not m.user.is_bot and not m.user.is_deleted:
            members.append((m.user.id, m.user.first_name))

    if len(members) < 2:
        await message.reply_text("Need at least two humans in here for that.")
        return

    pair = random.sample(members, 2)
    _couple_cache[message.chat.id] = (today, tuple(pair))
    await message.reply_text(f"💞 Today's couple: {mention_md(*pair[0])} & {mention_md(*pair[1])}")
