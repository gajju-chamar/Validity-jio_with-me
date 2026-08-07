import re

from pyrogram import Client, filters
from pyrogram.errors import RPCError
from pyrogram.types import ChatPermissions

from Reze.database.blacklist_db import add_word, remove_word, get_words, set_mode, get_mode
from Reze.utils.decorators import admins_only
from Reze.utils.helpers import is_exempt, mention_md

VALID_MODES = ("delete", "warn", "mute", "kick", "ban")
MUTE_PERMS = ChatPermissions()


@Client.on_message(filters.command(["addblacklist", "blacklist_add"]) & filters.group)
@admins_only(permission="can_change_info")
async def addblacklist_cmd(client, message):
    if len(message.command) < 2:
        await message.reply_text("Give me word(s) to blacklist, one per line or comma-separated.")
        return
    raw = message.text.split(None, 1)[1]
    words = [w.strip() for chunk in raw.split(",") for w in chunk.split("\n") if w.strip()]
    for w in words:
        await add_word(message.chat.id, w)
    await message.reply_text(f"Added {len(words)} word(s) to the blacklist.")


@Client.on_message(filters.command(["rmblacklist", "unblacklist"]) & filters.group)
@admins_only(permission="can_change_info")
async def rmblacklist_cmd(client, message):
    if len(message.command) < 2:
        await message.reply_text("Give me the word to remove.")
        return
    word = message.text.split(None, 1)[1].strip()
    await remove_word(message.chat.id, word)
    await message.reply_text(f"Removed `{word}` from the blacklist.")


@Client.on_message(filters.command(["blacklist", "blacklisted"]) & filters.group)
async def blacklist_list_cmd(client, message):
    words = await get_words(message.chat.id)
    mode = await get_mode(message.chat.id)
    if not words:
        await message.reply_text(f"No blacklisted words yet. Current action: **{mode}**.")
        return
    await message.reply_text(
        f"**Blacklisted words** (action: **{mode}**):\n" + ", ".join(f"`{w}`" for w in words)
    )


@Client.on_message(filters.command("blacklistmode") & filters.group)
@admins_only()
async def blacklistmode_cmd(client, message):
    if len(message.command) < 2 or message.command[1].lower() not in VALID_MODES:
        mode = await get_mode(message.chat.id)
        await message.reply_text(f"Current action: **{mode}**.\nSet with `/blacklistmode <{'|'.join(VALID_MODES)}>`.")
        return
    mode = message.command[1].lower()
    await set_mode(message.chat.id, mode)
    await message.reply_text(f"Blacklist hits will now trigger: **{mode}**.")


@Client.on_message(filters.group & filters.text, group=2)
async def enforce_blacklist(client, message):
    if not message.from_user:
        return
    words = await get_words(message.chat.id)
    if not words:
        return
    text_lower = message.text.lower()
    hit = next((w for w in words if re.search(rf"(?<!\w){re.escape(w)}(?!\w)", text_lower)), None)
    if not hit:
        return
    if await is_exempt(client, message.chat.id, message.from_user.id):
        return

    mode = await get_mode(message.chat.id)
    try:
        await message.delete()
    except RPCError:
        pass

    if mode == "delete":
        return

    try:
        if mode == "mute":
            await client.restrict_chat_member(message.chat.id, message.from_user.id, MUTE_PERMS)
            await client.send_message(message.chat.id, f"{mention_md(message.from_user.id, message.from_user.first_name)} got muted for a blacklisted word. 🔥")
        elif mode == "kick":
            await client.ban_chat_member(message.chat.id, message.from_user.id)
            await client.unban_chat_member(message.chat.id, message.from_user.id)
            await client.send_message(message.chat.id, f"{mention_md(message.from_user.id, message.from_user.first_name)} got kicked for a blacklisted word.")
        elif mode == "ban":
            await client.ban_chat_member(message.chat.id, message.from_user.id)
            await client.send_message(message.chat.id, f"{mention_md(message.from_user.id, message.from_user.first_name)} got banned for a blacklisted word. 🔥")
        elif mode == "warn":
            from Reze.database.warns_db import add_warn
            from Reze.database.chats_db import get_chat
            chat = await get_chat(message.chat.id)
            count = await add_warn(message.chat.id, message.from_user.id, f"blacklisted word: {hit}", client.me.id)
            if count >= chat["warn_limit"]:
                await client.ban_chat_member(message.chat.id, message.from_user.id)
                await client.send_message(message.chat.id, f"{mention_md(message.from_user.id, message.from_user.first_name)} hit the warn limit from blacklisted words and got banned.")
            else:
                await client.send_message(message.chat.id, f"{mention_md(message.from_user.id, message.from_user.first_name)} warned for a blacklisted word ({count}/{chat['warn_limit']}).")
    except RPCError:
        pass
