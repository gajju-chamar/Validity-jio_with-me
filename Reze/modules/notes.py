import re

from pyrogram import Client, filters

from Reze.database.notes_db import save_note, get_note, delete_note, list_notes
from Reze.utils.decorators import admins_only
from Reze.utils.helpers import capture_content


@Client.on_message(filters.command("save") & filters.group)
@admins_only(permission="can_change_info")
async def save_cmd(client, message):
    if len(message.command) < 2:
        await message.reply_text("Usage: `/save <name> <content>`, or reply to something with `/save <name>`.")
        return
    name = message.command[1]

    if message.reply_to_message:
        text, msg_type, file_id = capture_content(message.reply_to_message)
    else:
        rest = message.text.split(None, 2)
        text = rest[2] if len(rest) > 2 else ""
        msg_type, file_id = "text", None
        if not text:
            await message.reply_text("Give the note some content, or reply to a message to save that instead.")
            return

    await save_note(message.chat.id, name, text, msg_type, file_id)
    await message.reply_text(f"Saved note **{name}**. Get it with `/get {name}` or `#{name}`.")


@Client.on_message(filters.command(["get", "notes_get"]) & filters.group)
async def get_cmd(client, message):
    if len(message.command) < 2:
        await message.reply_text("Which note? `/get <name>`")
        return
    await _send_note(client, message, message.command[1])


@Client.on_message(filters.regex(r"^#(\w+)") & filters.group)
async def hashtag_note_cmd(client, message):
    name = re.match(r"^#(\w+)", message.text).group(1)
    note = await get_note(message.chat.id, name)
    if note:
        await _send_note(client, message, name)


async def _send_note(client, message, name):
    note = await get_note(message.chat.id, name)
    if not note:
        await message.reply_text(f"No note called **{name}** here.")
        return
    if note["msg_type"] == "text":
        await message.reply_text(note["content"] or "(empty note)")
    else:
        await client.send_cached_media(message.chat.id, note["file_id"], caption=note.get("content") or "",
                                        reply_to_message_id=message.id)


@Client.on_message(filters.command(["notes", "saved"]) & filters.group)
async def list_notes_cmd(client, message):
    names = await list_notes(message.chat.id)
    if not names:
        await message.reply_text("No notes saved in this chat yet.")
        return
    await message.reply_text(
        "**Saved notes:**\n" + "\n".join(f"• `{n}`" for n in names)
        + "\n\nGet one with `/get <name>` or `#<name>`."
    )


@Client.on_message(filters.command(["clear", "deletenote"]) & filters.group)
@admins_only(permission="can_change_info")
async def clear_note_cmd(client, message):
    if len(message.command) < 2:
        await message.reply_text("Which note should I clear? `/clear <name>`")
        return
    name = message.command[1]
    ok = await delete_note(message.chat.id, name)
    await message.reply_text(f"Cleared **{name}**." if ok else f"No note called **{name}**.")


@Client.on_message(filters.command("clearallnotes") & filters.group)
@admins_only(permission="can_change_info")
async def clear_all_notes_cmd(client, message):
    names = await list_notes(message.chat.id)
    for n in names:
        await delete_note(message.chat.id, n)
    await message.reply_text(f"Cleared all {len(names)} note(s).")
