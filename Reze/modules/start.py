from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from Reze.config import Config
from Reze.utils.reze import START_PRIVATE, START_GROUP
from Reze.modules._help_data import PAGE_1
from Reze.modules.help import _grid
from Reze.utils.reze import HELP_HEADER


def _private_start_markup(bot_username: str) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton("📖 Help", callback_data="help:page:1"),
         InlineKeyboardButton("➕ Add me to a group", url=f"https://t.me/{bot_username}?startgroup=true")],
    ]
    support_row = []
    if Config.SUPPORT_GROUP and Config.SUPPORT_GROUP != "https://t.me/":
        support_row.append(InlineKeyboardButton("💬 Support Group", url=Config.SUPPORT_GROUP))
    if Config.SUPPORT_CHANNEL and Config.SUPPORT_CHANNEL != "https://t.me/":
        support_row.append(InlineKeyboardButton("📣 Channel", url=Config.SUPPORT_CHANNEL))
    if support_row:
        rows.append(support_row)
    return InlineKeyboardMarkup(rows)


@Client.on_message(filters.command("start") & filters.private)
async def start_private(client, message):
    if len(message.command) > 1 and message.command[1].lower() == "help":
        await message.reply_text(HELP_HEADER, reply_markup=_grid(PAGE_1, 1))
        return

    text = START_PRIVATE.format(user=message.from_user.first_name or "there")
    await message.reply_text(
        text, reply_markup=_private_start_markup(client.me.username), disable_web_page_preview=True
    )


@Client.on_message(filters.command("start") & filters.group)
async def start_group(client, message):
    bot_username = client.me.username
    await message.reply_text(
        START_GROUP.format(chat=message.chat.title or "here"),
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("📖 Full help in PM", url=f"https://t.me/{bot_username}?start=help")
        ]]),
    )
