import re
from typing import Optional

from pyrogram.enums import MessageEntityType
from pyrogram.types import Message, User

from Reze.database.users_db import get_user_by_username

DURATION_RE = re.compile(r"^(\d+)([smhdw])$", re.IGNORECASE)
_UNIT_SECONDS = {"s": 1, "m": 60, "h": 3600, "d": 86400, "w": 604800}


async def extract_user(client, message: Message) -> Optional[User]:
    """Resolve the command's target user from a reply, an @username,
    a text-mention entity, or a raw numeric id in the command args."""
    if message.reply_to_message and message.reply_to_message.from_user:
        return message.reply_to_message.from_user

    if len(message.command) > 1:
        arg = message.command[1]

        if message.entities:
            for ent in message.entities:
                if ent.type == MessageEntityType.TEXT_MENTION:
                    return ent.user

        if arg.startswith("@"):
            doc = await get_user_by_username(arg.lstrip("@"))
            if doc:
                try:
                    return await client.get_users(doc["user_id"])
                except Exception:
                    return None
            try:
                return await client.get_users(arg)
            except Exception:
                return None

        if arg.isdigit() or (arg.startswith("-") and arg[1:].isdigit()):
            try:
                return await client.get_users(int(arg))
            except Exception:
                return None

    return None


def reason_from_command(message: Message, used_reply: bool) -> str:
    """Reason text: if replying, everything after `/cmd` is the reason.
    If targeting by @username/id, everything after that token is the reason."""
    if not message.text:
        return ""
    parts = message.text.split(maxsplit=2 if not used_reply else 1)
    if used_reply:
        return parts[1] if len(parts) > 1 else ""
    return parts[2] if len(parts) > 2 else ""


def parse_duration(text: str) -> Optional[int]:
    """'10m' -> 600, '1h' -> 3600, '2d' -> 172800. Returns None if invalid."""
    if not text:
        return None
    m = DURATION_RE.match(text.strip())
    if not m:
        return None
    value, unit = m.groups()
    return int(value) * _UNIT_SECONDS[unit.lower()]


def mention_md(user_id: int, name: str) -> str:
    safe = (name or "user").replace("[", "").replace("]", "")
    return f"[{safe}](tg://user?id={user_id})"


def human_list(items, empty="none yet") -> str:
    return ", ".join(items) if items else empty


def capture_content(message: Message):
    """Returns (content_text, msg_type, file_id) for a message so it can be
    replayed later via send_cached_media (media) or plain text."""
    for attr, kind in (
        ("sticker", "sticker"), ("photo", "photo"), ("video", "video"),
        ("animation", "animation"), ("document", "document"),
        ("audio", "audio"), ("voice", "voice"), ("video_note", "video_note"),
    ):
        obj = getattr(message, attr, None)
        if obj:
            file_id = obj.file_id
            text = message.caption or ""
            return text, kind, file_id
    return (message.text or ""), "text", None


async def is_exempt(client, chat_id: int, user_id: int) -> bool:
    """True if this user should skip automated enforcement (locks,
    blacklist, antiflood): chat admins, the bot owner, and approved users."""
    from Reze.config import Config
    from Reze.utils.decorators import is_admin_or_owner
    from Reze.database.approvals_db import is_approved

    if user_id in Config.SUDO_USERS:
        return True
    if await is_admin_or_owner(client, chat_id, user_id):
        return True
    if await is_approved(chat_id, user_id):
        return True
    return False
