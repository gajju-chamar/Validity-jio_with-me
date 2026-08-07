from pyrogram import Client, filters
from pyrogram.errors import RPCError

from Reze.database.chats_db import get_chat, set_welcome, set_goodbye
from Reze.utils.decorators import admins_only
from Reze.utils.helpers import mention_md

DEFAULT_WELCOME = "Heya {mention}, welcome to **{chatname}**! 🔥 Take a look around, and behave~"
DEFAULT_GOODBYE = "{first} just left. 🔥"

_last_welcome_msg = {}  # chat_id -> message_id, so we can clean up the previous one


def _fill(template: str, user, chat) -> str:
    fullname = " ".join(filter(None, [user.first_name, user.last_name]))
    return (
        template
        .replace("{mention}", mention_md(user.id, user.first_name))
        .replace("{first}", user.first_name or "")
        .replace("{last}", user.last_name or "")
        .replace("{fullname}", fullname or user.first_name or "")
        .replace("{username}", f"@{user.username}" if user.username else user.first_name)
        .replace("{chatname}", chat.title or "this chat")
        .replace("{id}", str(user.id))
    )


@Client.on_message(filters.new_chat_members, group=5)
async def welcome_new_member(client, message):
    chat = await get_chat(message.chat.id)
    wc = chat["welcome"]
    if not wc["enabled"]:
        return
    template = wc["text"] or DEFAULT_WELCOME

    if wc.get("clean_old"):
        old_id = _last_welcome_msg.get(message.chat.id)
        if old_id:
            try:
                await client.delete_messages(message.chat.id, old_id)
            except RPCError:
                pass

    for user in message.new_chat_members:
        if user.is_bot and user.id == client.me.id:
            continue
        text = _fill(template, user, message.chat)
        sent = await message.reply_text(text, disable_web_page_preview=True)
        _last_welcome_msg[message.chat.id] = sent.id


@Client.on_message(filters.left_chat_member, group=5)
async def goodbye_member(client, message):
    chat = await get_chat(message.chat.id)
    gb = chat["goodbye"]
    if not gb["enabled"] or not message.left_chat_member:
        return
    text = _fill(gb["text"] or DEFAULT_GOODBYE, message.left_chat_member, message.chat)
    await message.reply_text(text)


@Client.on_message(filters.command("setwelcome") & filters.group)
@admins_only(permission="can_change_info")
async def setwelcome_cmd(client, message):
    if len(message.command) < 2:
        await message.reply_text(
            "Give me the text after the command. Placeholders: "
            "`{mention} {first} {last} {fullname} {username} {chatname} {id}`"
        )
        return
    text = message.text.split(None, 1)[1]
    await set_welcome(message.chat.id, text=text, enabled=True)
    await message.reply_text("Welcome message updated.")


@Client.on_message(filters.command("resetwelcome") & filters.group)
@admins_only(permission="can_change_info")
async def resetwelcome_cmd(client, message):
    await set_welcome(message.chat.id, text=None)
    await message.reply_text("Welcome message reset to default.")


@Client.on_message(filters.command("welcome") & filters.group)
@admins_only(permission="can_change_info")
async def welcome_toggle_cmd(client, message):
    if len(message.command) < 2 or message.command[1].lower() not in ("on", "off"):
        chat = await get_chat(message.chat.id)
        state = "on" if chat["welcome"]["enabled"] else "off"
        await message.reply_text(f"Welcome messages are **{state}**.\nCurrent text:\n\n{chat['welcome']['text'] or DEFAULT_WELCOME}")
        return
    state = message.command[1].lower() == "on"
    await set_welcome(message.chat.id, enabled=state)
    await message.reply_text(f"Welcome messages are now **{'on' if state else 'off'}**.")


@Client.on_message(filters.command("setgoodbye") & filters.group)
@admins_only(permission="can_change_info")
async def setgoodbye_cmd(client, message):
    if len(message.command) < 2:
        await message.reply_text("Give me the text after the command. Same placeholders as `/setwelcome`.")
        return
    text = message.text.split(None, 1)[1]
    await set_goodbye(message.chat.id, text=text, enabled=True)
    await message.reply_text("Goodbye message updated.")


@Client.on_message(filters.command("goodbye") & filters.group)
@admins_only(permission="can_change_info")
async def goodbye_toggle_cmd(client, message):
    if len(message.command) < 2 or message.command[1].lower() not in ("on", "off"):
        chat = await get_chat(message.chat.id)
        state = "on" if chat["goodbye"]["enabled"] else "off"
        await message.reply_text(f"Goodbye messages are **{state}**.")
        return
    state = message.command[1].lower() == "on"
    await set_goodbye(message.chat.id, enabled=state)
    await message.reply_text(f"Goodbye messages are now **{'on' if state else 'off'}**.")
