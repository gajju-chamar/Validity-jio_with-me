"""
A single dashboard for the toggles people otherwise have to hunt across
separate commands for - the Control button in /help.
"""
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from Reze.database.chats_db import get_chat, set_antiflood, set_welcome, set_flag
from Reze.utils.decorators import admins_only

TOGGLES = [
    ("antiflood", "🌊 Antiflood", lambda c: c["antiflood"]["enabled"]),
    ("anti_channel", "📡 Anti-channel", lambda c: c.get("anti_channel", False)),
    ("welcome", "👋 Welcome messages", lambda c: c["welcome"]["enabled"]),
    ("reports_enabled", "🚩 Reporting", lambda c: c.get("reports_enabled", True)),
]


def _markup(chat: dict) -> InlineKeyboardMarkup:
    rows = []
    for field, label, getter in TOGGLES:
        state = "🟢" if getter(chat) else "🔴"
        rows.append([InlineKeyboardButton(f"{state} {label}", callback_data=f"control:toggle:{field}")])
    rows.append([InlineKeyboardButton("Close", callback_data="control:close")])
    return InlineKeyboardMarkup(rows)


def _summary(chat: dict) -> str:
    locked = sum(1 for v in chat["locks"].values() if v)
    return (
        f"**Control panel — {chat.get('title') or 'this chat'}**\n\n"
        f"🔒 Locks active: {locked}/{len(chat['locks'])} (see `/locks` for detail)\n"
        f"⚠️ Warn limit: {chat['warn_limit']} → {chat['warn_mode']}\n\n"
        f"Tap to flip a toggle:"
    )


@Client.on_message(filters.command("control") & filters.group)
@admins_only()
async def control_cmd(client, message):
    chat = await get_chat(message.chat.id)
    await message.reply_text(_summary(chat), reply_markup=_markup(chat))


@Client.on_callback_query(filters.regex(r"^control:"))
async def control_callback(client, query):
    if not query.message.chat or query.from_user is None:
        await query.answer()
        return
    from Reze.utils.decorators import is_admin_or_owner
    if not await is_admin_or_owner(client, query.message.chat.id, query.from_user.id):
        await query.answer("Admins only.", show_alert=True)
        return

    data = query.data.split(":")
    action = data[1]

    if action == "close":
        await query.message.delete()
        await query.answer()
        return

    field = data[2]
    chat = await get_chat(query.message.chat.id)
    getter = next(g for f, _, g in TOGGLES if f == field)
    new_state = not getter(chat)

    if field == "antiflood":
        await set_antiflood(query.message.chat.id, enabled=new_state)
    elif field == "welcome":
        await set_welcome(query.message.chat.id, enabled=new_state)
    else:
        await set_flag(query.message.chat.id, field, new_state)

    chat = await get_chat(query.message.chat.id)
    await query.message.edit_text(_summary(chat), reply_markup=_markup(chat))
    await query.answer(f"{'Enabled' if new_state else 'Disabled'}.")
