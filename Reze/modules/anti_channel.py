"""
Blocks messages auto-posted by a linked discussion channel, without
blocking admins who post anonymously as the group itself (sender_chat
equal to the group's own id is a normal anonymous-admin post, not a
foreign channel forwarding in).
"""
from pyrogram import Client, filters
from pyrogram.errors import RPCError

from Reze.database.chats_db import get_chat, set_flag
from Reze.utils.decorators import admins_only


@Client.on_message(filters.command("antichannel") & filters.group)
@admins_only()
async def antichannel_toggle_cmd(client, message):
    if len(message.command) < 2 or message.command[1].lower() not in ("on", "off"):
        chat = await get_chat(message.chat.id)
        state = "on" if chat.get("anti_channel") else "off"
        await message.reply_text(f"Anti-channel is **{state}**. Use `/antichannel on` or `/antichannel off`.")
        return
    state = message.command[1].lower() == "on"
    await set_flag(message.chat.id, "anti_channel", state)
    await message.reply_text(f"Anti-channel is now **{state and 'on' or 'off'}**.")


@Client.on_message(filters.group, group=2)
async def enforce_anti_channel(client, message):
    if not message.sender_chat:
        return
    if message.sender_chat.id == message.chat.id:
        return  # anonymous admin posting as the group itself - allowed
    chat = await get_chat(message.chat.id)
    if not chat.get("anti_channel"):
        return
    try:
        await message.delete()
    except RPCError:
        pass
