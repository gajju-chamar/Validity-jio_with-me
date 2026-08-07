from pyrogram import Client, filters
from pyrogram.enums import ChatMembersFilter

from Reze.database.chats_db import get_chat, set_flag
from Reze.utils.decorators import admins_only, is_admin_or_owner
from Reze.utils.helpers import mention_md


@Client.on_message(filters.command("report") & filters.group)
async def report_cmd(client, message):
    await _do_report(client, message)


@Client.on_message(filters.regex(r"(?i)^@admin(s)?\b") & filters.group)
async def at_admin_cmd(client, message):
    await _do_report(client, message)


async def _do_report(client, message):
    chat = await get_chat(message.chat.id)
    if not chat.get("reports_enabled", True):
        return
    if not message.reply_to_message:
        await message.reply_text("Reply to the message you're reporting.")
        return
    if await is_admin_or_owner(client, message.chat.id, message.from_user.id):
        return  # admins reporting isn't useful - they can just act

    reported = message.reply_to_message.from_user
    tags = []
    async for member in client.get_chat_members(message.chat.id, filter=ChatMembersFilter.ADMINISTRATORS):
        if not member.user.is_bot:
            tags.append(mention_md(member.user.id, member.user.first_name))
    if not tags:
        return
    who = mention_md(reported.id, reported.first_name) if reported else "that message"
    await message.reply_to_message.reply_text(
        f"🔥 Reported to admins: {' '.join(tags)}\n{mention_md(message.from_user.id, message.from_user.first_name)} flagged {who}."
    )


@Client.on_message(filters.command("reports") & filters.group)
@admins_only()
async def reports_toggle_cmd(client, message):
    if len(message.command) < 2 or message.command[1].lower() not in ("on", "off"):
        chat = await get_chat(message.chat.id)
        state = "on" if chat.get("reports_enabled", True) else "off"
        await message.reply_text(f"Reporting is **{state}**. Use `/reports on` or `/reports off`.")
        return
    state = message.command[1].lower() == "on"
    await set_flag(message.chat.id, "reports_enabled", state)
    await message.reply_text(f"Reporting is now **{'on' if state else 'off'}**.")
