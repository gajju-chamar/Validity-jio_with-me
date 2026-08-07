import functools

from pyrogram.enums import ChatMemberStatus, ChatType

from Reze.config import Config
from Reze.utils.reze import pick, NOT_ADMIN_LINES, BOT_NOT_ADMIN_LINES


async def is_admin_or_owner(client, chat_id: int, user_id: int) -> bool:
    if user_id in Config.SUDO_USERS:
        return True
    try:
        member = await client.get_chat_member(chat_id, user_id)
    except Exception:
        return False
    return member.status in (ChatMemberStatus.OWNER, ChatMemberStatus.ADMINISTRATOR)


async def has_permission(client, chat_id: int, user_id: int, permission: str) -> bool:
    """permission is a ChatPrivileges field name, e.g. 'can_restrict_members'."""
    if user_id in Config.SUDO_USERS:
        return True
    try:
        member = await client.get_chat_member(chat_id, user_id)
    except Exception:
        return False
    if member.status == ChatMemberStatus.OWNER:
        return True
    if member.status != ChatMemberStatus.ADMINISTRATOR:
        return False
    if member.privileges is None:
        return False
    return bool(getattr(member.privileges, permission, False))


def admins_only(permission: str = None):
    """Gate a handler to admins only. If `permission` is given, requires
    that specific privilege rather than just any admin status."""
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(client, message, *args, **kwargs):
            if message.chat.type == ChatType.PRIVATE:
                return await func(client, message, *args, **kwargs)
            ok = (
                await has_permission(client, message.chat.id, message.from_user.id, permission)
                if permission else
                await is_admin_or_owner(client, message.chat.id, message.from_user.id)
            )
            if not ok:
                await message.reply_text(pick(NOT_ADMIN_LINES))
                return
            return await func(client, message, *args, **kwargs)
        return wrapper
    return decorator


def bot_admin_required(permission: str = None):
    """Gate a handler behind the BOT itself having admin / a specific
    privilege in this chat, so we fail with a clear message instead of
    a raw Telegram FORBIDDEN error."""
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(client, message, *args, **kwargs):
            if message.chat.type == ChatType.PRIVATE:
                return await func(client, message, *args, **kwargs)
            bot_id = client.me.id
            ok = (
                await has_permission(client, message.chat.id, bot_id, permission)
                if permission else
                await is_admin_or_owner(client, message.chat.id, bot_id)
            )
            if not ok:
                await message.reply_text(pick(BOT_NOT_ADMIN_LINES))
                return
            return await func(client, message, *args, **kwargs)
        return wrapper
    return decorator


def owner_only(func):
    @functools.wraps(func)
    async def wrapper(client, message, *args, **kwargs):
        if message.from_user is None or message.from_user.id not in Config.SUDO_USERS:
            await message.reply_text("This one's mine to handle. 🔥")
            return
        return await func(client, message, *args, **kwargs)
    return wrapper
