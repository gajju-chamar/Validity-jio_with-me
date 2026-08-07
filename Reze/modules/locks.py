"""
Locks - block specific content types from non-admins. Two halves:
the /lock /unlock commands, and the always-on enforcement handler that
actually deletes matching content from anyone who isn't exempt.
"""
from pyrogram import Client, filters
from pyrogram.errors import RPCError

try:
    import emoji as _emoji_lib
except ImportError:
    _emoji_lib = None

from Reze.database.chats_db import get_locks, set_lock
from Reze.utils.decorators import admins_only, bot_admin_required
from Reze.utils.helpers import is_exempt

LOCK_ALIASES = {
    "sticker": "sticker", "stickers": "sticker",
    "photo": "photo", "photos": "photo", "pic": "photo", "pics": "photo",
    "video": "video", "videos": "video",
    "gif": "gif", "gifs": "gif", "animation": "gif",
    "url": "url", "urls": "url", "link": "url", "links": "url",
    "forward": "forward", "forwarded": "forward",
    "game": "game", "games": "game",
    "location": "location", "venue": "location",
    "audio": "audio", "music": "audio",
    "contact": "contact",
    "document": "document", "file": "document", "files": "document",
    "poll": "poll", "polls": "poll",
    "voice": "voice",
    "videonote": "videonote", "round": "videonote",
    "inline": "inline",
    "emoji": "emoji", "emojis": "emoji",
    "bot": "bot", "bots": "bot",
}


@Client.on_message(filters.command("lock") & filters.group)
@admins_only(permission="can_change_info")
@bot_admin_required(permission="can_delete_messages")
async def lock_cmd(client, message):
    if len(message.command) < 2:
        await message.reply_text("Lock what? e.g. `/lock sticker` — see `/locktypes` for the full list.")
        return
    key = LOCK_ALIASES.get(message.command[1].lower())
    if not key:
        await message.reply_text("Don't know that lock type. Check `/locktypes`.")
        return
    await set_lock(message.chat.id, key, True)
    await message.reply_text(f"🔒 **{key}** is now locked for everyone except admins.")


@Client.on_message(filters.command("unlock") & filters.group)
@admins_only(permission="can_change_info")
async def unlock_cmd(client, message):
    if len(message.command) < 2:
        await message.reply_text("Unlock what? e.g. `/unlock sticker`")
        return
    key = LOCK_ALIASES.get(message.command[1].lower())
    if not key:
        await message.reply_text("Don't know that lock type. Check `/locktypes`.")
        return
    await set_lock(message.chat.id, key, False)
    await message.reply_text(f"🔓 **{key}** is unlocked.")


@Client.on_message(filters.command("locks") & filters.group)
async def locks_cmd(client, message):
    locks = await get_locks(message.chat.id)
    lines = [f"{'🔒' if v else '🔓'} {k}" for k, v in locks.items()]
    await message.reply_text("**Current locks:**\n" + "\n".join(lines))


@Client.on_message(filters.command("locktypes"))
async def locktypes_cmd(client, message):
    await message.reply_text("**Lockable types:**\n" + ", ".join(sorted(set(LOCK_ALIASES.values()))))


def _message_lock_key(message) -> str:
    if message.sticker:
        return "sticker"
    if message.photo:
        return "photo"
    if message.video:
        return "video"
    if message.animation:
        return "gif"
    if message.audio:
        return "audio"
    if message.voice:
        return "voice"
    if message.video_note:
        return "videonote"
    if message.document:
        return "document"
    if message.contact:
        return "contact"
    if message.location or message.venue:
        return "location"
    if message.poll:
        return "poll"
    if message.game:
        return "game"
    if message.via_bot:
        return "inline"
    if getattr(message, "forward_date", None) or getattr(message, "forward_origin", None):
        return "forward"
    if message.text:
        if any(e.type.name in ("URL", "TEXT_LINK") for e in (message.entities or [])):
            return "url"
        if _emoji_lib and message.text.strip() and _emoji_lib.emoji_count(message.text) >= len(message.text.strip()):
            return "emoji"
    return None


@Client.on_message(filters.group & ~filters.service, group=2)
async def enforce_locks(client, message):
    if not message.from_user:
        return
    key = _message_lock_key(message)
    if not key:
        return
    locks = await get_locks(message.chat.id)
    if not locks.get(key):
        return
    if await is_exempt(client, message.chat.id, message.from_user.id):
        return
    try:
        await message.delete()
    except RPCError:
        pass


@Client.on_chat_member_updated(filters.group, group=2)
async def enforce_bot_lock(client, update):
    """If 'bot' is locked, a non-admin adding another bot gets that bot removed."""
    new = update.new_chat_member
    if not new or not new.user or not new.user.is_bot:
        return
    if new.user.id == client.me.id:
        return
    locks = await get_locks(update.chat.id)
    if not locks.get("bot"):
        return
    adder_id = update.from_user.id if update.from_user else None
    if adder_id and await is_exempt(client, update.chat.id, adder_id):
        return
    try:
        await client.ban_chat_member(update.chat.id, new.user.id)
        await client.unban_chat_member(update.chat.id, new.user.id)
    except RPCError:
        pass
