"""
Requires membership in a channel before someone can post in the group.
"""
from pyrogram import Client, filters
from pyrogram.errors import RPCError, UserNotParticipant
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from Reze.database.chats_db import get_chat, set_fsub
from Reze.utils.decorators import admins_only
from Reze.utils.helpers import is_exempt


@Client.on_message(filters.command("fsub") & filters.group)
@admins_only(permission="can_change_info")
async def fsub_cmd(client, message):
    if len(message.command) < 2:
        chat = await get_chat(message.chat.id)
        fs = chat.get("fsub", {})
        if fs.get("enabled"):
            await message.reply_text(f"F-Sub is on, requiring: `{fs.get('channel_id')}`.\n`/fsub off` to disable.")
        else:
            await message.reply_text("F-Sub is off. Set it with `/fsub @channelusername`.")
        return

    arg = message.command[1]
    if arg.lower() == "off":
        await set_fsub(message.chat.id, enabled=False)
        await message.reply_text("F-Sub disabled.")
        return

    try:
        target_chat = await client.get_chat(arg)
    except RPCError as e:
        await message.reply_text(f"Couldn't find that channel. (`{e}`)")
        return
    await set_fsub(message.chat.id, enabled=True, channel_id=target_chat.id)
    await message.reply_text(f"F-Sub is on — members must join **{target_chat.title}** to post here.")


@Client.on_message(filters.group & filters.text, group=1)
async def enforce_fsub(client, message):
    if not message.from_user:
        return
    chat = await get_chat(message.chat.id)
    fs = chat.get("fsub", {})
    if not fs.get("enabled") or not fs.get("channel_id"):
        return
    if await is_exempt(client, message.chat.id, message.from_user.id):
        return
    try:
        await client.get_chat_member(fs["channel_id"], message.from_user.id)
    except UserNotParticipant:
        try:
            invite_chat = await client.get_chat(fs["channel_id"])
            if invite_chat.invite_link:
                link = invite_chat.invite_link
            elif invite_chat.username:
                link = f"https://t.me/{invite_chat.username}"
            else:
                link = None
        except RPCError:
            link = None
        try:
            await message.delete()
        except RPCError:
            pass
        markup = InlineKeyboardMarkup([[InlineKeyboardButton("Join the channel", url=link)]]) if link else None
        await client.send_message(
            message.chat.id,
            f"{message.from_user.first_name}, join the required channel first, then send your message again. 🔥",
            reply_markup=markup,
        )
    except RPCError:
        pass
