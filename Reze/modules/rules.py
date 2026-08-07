from pyrogram import Client, filters
from pyrogram.enums import ChatType

from Reze.database.chats_db import get_chat, set_rules
from Reze.utils.decorators import admins_only


@Client.on_message(filters.command("setrules") & filters.group)
@admins_only(permission="can_change_info")
async def setrules_cmd(client, message):
    if len(message.command) < 2:
        await message.reply_text("Give me the rules text after the command.")
        return
    text = message.text.split(None, 1)[1]
    await set_rules(message.chat.id, text)
    await message.reply_text("Rules updated. `/rules` will show this now.")


@Client.on_message(filters.command("rules"))
async def rules_cmd(client, message):
    if message.chat.type == ChatType.PRIVATE:
        await message.reply_text("Use `/rules` inside a group to see that group's rules.")
        return
    chat = await get_chat(message.chat.id)
    if not chat.get("rules"):
        await message.reply_text("No rules have been set for this chat yet.")
        return
    try:
        await client.send_message(
            message.from_user.id,
            f"**Rules for {message.chat.title}:**\n\n{chat['rules']}",
        )
        await message.reply_text("Sent you the rules in PM. 🔥")
    except Exception:
        await message.reply_text(f"**Rules for {message.chat.title}:**\n\n{chat['rules']}")


@Client.on_message(filters.command("clearrules") & filters.group)
@admins_only(permission="can_change_info")
async def clearrules_cmd(client, message):
    await set_rules(message.chat.id, None)
    await message.reply_text("Rules cleared.")
