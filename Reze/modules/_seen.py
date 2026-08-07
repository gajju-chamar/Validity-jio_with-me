"""Passively logs every user/message author seen, so @username lookups
work later (extract_user) without needing the bot to already be admin."""
from pyrogram import Client, filters

from Reze.database.users_db import log_user
from Reze.database.chats_db import set_chat_title


@Client.on_message(filters.group | filters.private, group=-1)
async def _track_seen(client, message):
    if message.from_user:
        await log_user(
            message.from_user.id,
            message.from_user.username,
            message.from_user.first_name,
        )
    if message.chat and message.chat.title:
        await set_chat_title(message.chat.id, message.chat.title)
