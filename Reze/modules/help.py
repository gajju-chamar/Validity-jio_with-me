from pyrogram import Client, filters
from pyrogram.enums import ChatType
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import RPCError

from Reze.modules._help_data import PAGE_1, PAGE_2, get_description, find_by_label
from Reze.utils.reze import HELP_HEADER, ABOUT_TEXT


def _grid(modules_page, page_num: int) -> InlineKeyboardMarkup:
    rows = []
    for i in range(0, len(modules_page), 3):
        row = [
            InlineKeyboardButton(label, callback_data=f"help:mod:{key}")
            for label, key, _ in modules_page[i:i + 3]
        ]
        rows.append(row)
    nav = []
    if page_num == 2:
        nav.append(InlineKeyboardButton("«", callback_data="help:page:1"))
    else:
        nav.append(InlineKeyboardButton("«", callback_data="help:noop"))
    nav.append(InlineKeyboardButton("Back", callback_data="help:close"))
    if page_num == 1:
        nav.append(InlineKeyboardButton("»", callback_data="help:page:2"))
    else:
        nav.append(InlineKeyboardButton("»", callback_data="help:noop"))
    rows.append(nav)
    return InlineKeyboardMarkup(rows)


def _module_detail_markup(page_num: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton("« Back to menu", callback_data=f"help:page:{page_num}")]])


@Client.on_message(filters.command("help"))
async def help_cmd(client, message):
    if len(message.command) > 1:
        query = message.text.split(None, 1)[1]
        key, desc = find_by_label(query)
        if not desc:
            await message.reply_text(f"No module called **{query}**. Use `/help` to see the full list.")
            return
        text = f"**{query.title()}**\n\n{desc}"
        if message.chat.type == ChatType.PRIVATE:
            await message.reply_text(text)
        else:
            try:
                await client.send_message(message.from_user.id, text)
                await message.reply_text("Sent that to your PM. 🔥")
            except RPCError:
                await message.reply_text(text)
        return

    if message.chat.type != ChatType.PRIVATE:
        bot_username = client.me.username
        await message.reply_text(
            "I'll keep the full menu tidy in PM — tap below. 🔥",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("Open Help in PM", url=f"https://t.me/{bot_username}?start=help")
            ]]),
        )
        return

    await message.reply_text(HELP_HEADER, reply_markup=_grid(PAGE_1, 1))


@Client.on_callback_query(filters.regex(r"^help:"))
async def help_callback(client, query):
    data = query.data.split(":")
    action = data[1]

    if action == "noop":
        await query.answer()
        return

    if action == "page":
        page_num = int(data[2])
        page = PAGE_1 if page_num == 1 else PAGE_2
        await query.message.edit_text(HELP_HEADER, reply_markup=_grid(page, page_num))
        await query.answer()
        return

    if action == "close":
        await query.message.edit_text(ABOUT_TEXT)
        await query.answer()
        return

    if action == "mod":
        key = data[2]
        result = get_description(key)
        if not result:
            await query.answer("Couldn't find that module.", show_alert=True)
            return
        label, desc = result
        page_num = 1 if any(m[1] == key for m in PAGE_1) else 2
        await query.message.edit_text(
            f"**{label}**\n\n{desc}", reply_markup=_module_detail_markup(page_num)
        )
        await query.answer()
        return

    await query.answer()
