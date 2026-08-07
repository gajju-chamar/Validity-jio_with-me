from pyrogram import Client, filters
from pyrogram.errors import RPCError
from pyrogram.types import ChatPermissions

from Reze.database.warns_db import add_warn, get_warns, reset_warns, remove_last_warn
from Reze.database.chats_db import get_chat, set_warn_limit, set_warn_mode
from Reze.utils.decorators import admins_only, bot_admin_required
from Reze.utils.helpers import extract_user, mention_md, reason_from_command
from Reze.utils.reze import pick, GENERIC_ERROR_LINES

MUTE_PERMS = ChatPermissions()


async def _apply_warn_action(client, message, target, mode: str):
    try:
        if mode == "ban":
            await client.ban_chat_member(message.chat.id, target.id)
            return "banned"
        elif mode == "kick":
            await client.ban_chat_member(message.chat.id, target.id)
            await client.unban_chat_member(message.chat.id, target.id)
            return "kicked"
        else:  # mute
            await client.restrict_chat_member(message.chat.id, target.id, MUTE_PERMS)
            return "muted"
    except RPCError:
        return None


@Client.on_message(filters.command("warn") & filters.group)
@admins_only(permission="can_restrict_members")
@bot_admin_required(permission="can_restrict_members")
async def warn_cmd(client, message):
    target = await extract_user(client, message)
    if target is None:
        await message.reply_text("Reply to a message, or give me a @username / id to warn.")
        return
    if target.id == client.me.id:
        await message.reply_text("I don't warn myself. 🔥")
        return

    reason = reason_from_command(message, used_reply=bool(message.reply_to_message))
    chat = await get_chat(message.chat.id)
    count = await add_warn(message.chat.id, target.id, reason, message.from_user.id)
    limit = chat["warn_limit"]

    if count >= limit:
        action = await _apply_warn_action(client, message, target, chat["warn_mode"])
        await reset_warns(message.chat.id, target.id)
        if action:
            await message.reply_text(
                f"{mention_md(target.id, target.first_name)} hit {count}/{limit} warns and got {action}. "
                f"That's the deal. 🔥"
            )
        else:
            await message.reply_text(f"{pick(GENERIC_ERROR_LINES)} (couldn't apply {chat['warn_mode']})")
        return

    text = f"{mention_md(target.id, target.first_name)} warned ({count}/{limit})."
    if reason:
        text += f"\n**Reason:** {reason}"
    await message.reply_text(text)


@Client.on_message(filters.command(["warns", "checkwarns"]) & filters.group)
async def warns_cmd(client, message):
    target = await extract_user(client, message) or message.from_user
    warns = await get_warns(message.chat.id, target.id)
    chat = await get_chat(message.chat.id)
    if not warns:
        await message.reply_text(f"{mention_md(target.id, target.first_name)} has a clean record. 0/{chat['warn_limit']}.")
        return
    lines = [f"{i+1}. {w['reason']}" for i, w in enumerate(warns)]
    await message.reply_text(
        f"{mention_md(target.id, target.first_name)} — {len(warns)}/{chat['warn_limit']} warns:\n" + "\n".join(lines)
    )


@Client.on_message(filters.command(["resetwarn", "resetwarns"]) & filters.group)
@admins_only(permission="can_restrict_members")
async def resetwarn_cmd(client, message):
    target = await extract_user(client, message)
    if target is None:
        await message.reply_text("Reply to a message, or give me a @username / id.")
        return
    await reset_warns(message.chat.id, target.id)
    await message.reply_text(f"{mention_md(target.id, target.first_name)}'s warns are cleared.")


@Client.on_message(filters.command(["removewarn", "unwarn"]) & filters.group)
@admins_only(permission="can_restrict_members")
async def removewarn_cmd(client, message):
    target = await extract_user(client, message)
    if target is None:
        await message.reply_text("Reply to a message, or give me a @username / id.")
        return
    ok = await remove_last_warn(message.chat.id, target.id)
    await message.reply_text(
        f"Removed one warn from {mention_md(target.id, target.first_name)}." if ok
        else f"{mention_md(target.id, target.first_name)} has no warns to remove."
    )


@Client.on_message(filters.command("warnlimit") & filters.group)
@admins_only()
async def warnlimit_cmd(client, message):
    if len(message.command) < 2 or not message.command[1].isdigit():
        chat = await get_chat(message.chat.id)
        await message.reply_text(f"Current warn limit: **{chat['warn_limit']}**.\nSet it with `/warnlimit <number>`.")
        return
    limit = max(1, int(message.command[1]))
    await set_warn_limit(message.chat.id, limit)
    await message.reply_text(f"Warn limit set to **{limit}**.")


@Client.on_message(filters.command("warnmode") & filters.group)
@admins_only()
async def warnmode_cmd(client, message):
    valid = ("ban", "kick", "mute")
    if len(message.command) < 2 or message.command[1].lower() not in valid:
        chat = await get_chat(message.chat.id)
        await message.reply_text(
            f"Current warn action: **{chat['warn_mode']}**.\nSet it with `/warnmode <ban|kick|mute>`."
        )
        return
    mode = message.command[1].lower()
    await set_warn_mode(message.chat.id, mode)
    await message.reply_text(f"Reaching the warn limit will now **{mode}** the user.")
