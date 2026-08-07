"""
Covers both the Mentions and Tagger buttons in /help - one engine,
/tagall pings everyone with an optional message attached.
"""
import asyncio

from pyrogram import Client, filters
from pyrogram.enums import ChatMembersFilter
from pyrogram.errors import RPCError

from Reze.utils.decorators import admins_only
from Reze.utils.helpers import mention_md

CHUNK_SIZE = 5


@Client.on_message(filters.command(["tagall", "tag"]) & filters.group)
@admins_only()
async def tagall_cmd(client, message):
    note = message.text.split(None, 1)[1] if len(message.command) > 1 else ""
    mentions = []
    async for member in client.get_chat_members(message.chat.id, filter=ChatMembersFilter.RECENT):
        if member.user and not member.user.is_bot and not member.user.is_deleted:
            mentions.append(mention_md(member.user.id, member.user.first_name))

    if not mentions:
        await message.reply_text("Couldn't find anyone to tag.")
        return

    header = f"{note}\n" if note else ""
    for i in range(0, len(mentions), CHUNK_SIZE):
        chunk = " ".join(mentions[i:i + CHUNK_SIZE])
        try:
            await message.reply_text(f"{header}{chunk}")
        except RPCError:
            pass
        await asyncio.sleep(1.2)  # stay well clear of flood limits on big chats
