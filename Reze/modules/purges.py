from pyrogram import Client, filters
from pyrogram.errors import RPCError

from Reze.utils.decorators import admins_only, bot_admin_required

_purge_marks = {}  # chat_id -> message_id marked by /purgefrom, consumed by /purgeto


@Client.on_message(filters.command("del") & filters.group)
@admins_only(permission="can_delete_messages")
@bot_admin_required(permission="can_delete_messages")
async def del_cmd(client, message):
    if not message.reply_to_message:
        await message.reply_text("Reply to the message you want deleted.")
        return
    try:
        await message.reply_to_message.delete()
        await message.delete()
    except RPCError:
        await message.reply_text("Couldn't delete that.")


@Client.on_message(filters.command("purge") & filters.group)
@admins_only(permission="can_delete_messages")
@bot_admin_required(permission="can_delete_messages")
async def purge_cmd(client, message):
    if not message.reply_to_message:
        await message.reply_text("Reply to the message to start purging from.")
        return
    start_id = message.reply_to_message.id
    end_id = message.id
    ids = list(range(start_id, end_id + 1))
    deleted = 0
    for i in range(0, len(ids), 100):
        chunk = ids[i:i + 100]
        try:
            deleted += await client.delete_messages(message.chat.id, chunk)
        except RPCError:
            continue
    try:
        note = await client.send_message(message.chat.id, f"Purged {deleted} message(s). 🔥")
        import asyncio
        await asyncio.sleep(3)
        await note.delete()
    except RPCError:
        pass


@Client.on_message(filters.command("purgefrom") & filters.group)
@admins_only(permission="can_delete_messages")
@bot_admin_required(permission="can_delete_messages")
async def purgefrom_cmd(client, message):
    if not message.reply_to_message:
        await message.reply_text("Reply to the message to mark as the purge start point, then use `/purgeto` on the end message.")
        return
    _purge_marks[message.chat.id] = message.reply_to_message.id
    await message.reply_text("Marked. Now reply to the end message with `/purgeto`.")


@Client.on_message(filters.command("purgeto") & filters.group)
@admins_only(permission="can_delete_messages")
@bot_admin_required(permission="can_delete_messages")
async def purgeto_cmd(client, message):
    start_id = _purge_marks.pop(message.chat.id, None)
    if not start_id or not message.reply_to_message:
        await message.reply_text("Use `/purgefrom` on the start message first, then reply to the end message with `/purgeto`.")
        return
    ids = list(range(start_id, message.reply_to_message.id + 1))
    deleted = 0
    for i in range(0, len(ids), 100):
        chunk = ids[i:i + 100]
        try:
            deleted += await client.delete_messages(message.chat.id, chunk)
        except RPCError:
            continue
    await message.reply_text(f"Purged {deleted} message(s). 🔥")
