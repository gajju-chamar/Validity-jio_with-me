"""
Admins module - the muscle. Ban, mute, kick, promote, pin, and friends.
Every destructive action checks the sender's permission AND the bot's own
permission before touching anything (see utils/decorators.py), and refuses
to act on fellow admins or the chat owner.
"""
from datetime import datetime, timedelta

from pyrogram import Client, filters
from pyrogram.enums import ChatMemberStatus, ChatMembersFilter
from pyrogram.types import ChatPermissions, ChatPrivileges
from pyrogram.errors import RPCError

from Reze.config import Config
from Reze.utils.decorators import admins_only, bot_admin_required
from Reze.utils.helpers import extract_user, parse_duration, mention_md, reason_from_command
from Reze.utils.reze import pick, TARGET_IS_ADMIN_LINES, CANT_ACTION_OWNER, GENERIC_ERROR_LINES

MUTE_PERMS = ChatPermissions()                 # nothing specified -> restricts everything
UNMUTE_PERMS = ChatPermissions(all_perms=True)  # restores every permission


async def _guard_target(client, message, target):
    """Shared checks: no target found / target is self-bot / target outranks
    the caller. Returns True if the action should proceed."""
    if target is None:
        await message.reply_text(
            "Reply to a message, or give me a @username / user id to act on. 🔥"
        )
        return False
    if target.id == client.me.id:
        await message.reply_text("I'm not restraining myself on your behalf.")
        return False
    try:
        member = await client.get_chat_member(message.chat.id, target.id)
    except RPCError:
        return True  # target may have already left - let the real API call surface any error

    if member.status == ChatMemberStatus.OWNER:
        await message.reply_text(CANT_ACTION_OWNER)
        return False

    if member.status == ChatMemberStatus.ADMINISTRATOR:
        # a plain admin can't touch a fellow admin - only the owner or sudo can
        actor_is_owner = False
        try:
            actor = await client.get_chat_member(message.chat.id, message.from_user.id)
            actor_is_owner = actor.status == ChatMemberStatus.OWNER
        except RPCError:
            pass
        if not (actor_is_owner or message.from_user.id in Config.SUDO_USERS):
            await message.reply_text(pick(TARGET_IS_ADMIN_LINES))
            return False
    return True


# ---------------------------------------------------------------- ban/kick
@Client.on_message(filters.command("ban") & filters.group)
@admins_only(permission="can_restrict_members")
@bot_admin_required(permission="can_restrict_members")
async def ban_cmd(client, message):
    target = await extract_user(client, message)
    if not await _guard_target(client, message, target):
        return
    reason = reason_from_command(message, used_reply=bool(message.reply_to_message))
    try:
        await client.ban_chat_member(message.chat.id, target.id)
    except RPCError as e:
        await message.reply_text(f"{pick(GENERIC_ERROR_LINES)} (`{e}`)")
        return
    text = f"{mention_md(target.id, target.first_name)} has been banned. 🔥"
    if reason:
        text += f"\n**Reason:** {reason}"
    await message.reply_text(text)


@Client.on_message(filters.command("unban") & filters.group)
@admins_only(permission="can_restrict_members")
@bot_admin_required(permission="can_restrict_members")
async def unban_cmd(client, message):
    target = await extract_user(client, message)
    if target is None:
        await message.reply_text("Who am I unbanning? Reply or give me a @username / id.")
        return
    try:
        await client.unban_chat_member(message.chat.id, target.id)
    except RPCError as e:
        await message.reply_text(f"{pick(GENERIC_ERROR_LINES)} (`{e}`)")
        return
    await message.reply_text(f"{mention_md(target.id, target.first_name)} is unbanned. Clean slate.")


@Client.on_message(filters.command("kick") & filters.group)
@admins_only(permission="can_restrict_members")
@bot_admin_required(permission="can_restrict_members")
async def kick_cmd(client, message):
    target = await extract_user(client, message)
    if not await _guard_target(client, message, target):
        return
    reason = reason_from_command(message, used_reply=bool(message.reply_to_message))
    try:
        await client.ban_chat_member(message.chat.id, target.id)
        await client.unban_chat_member(message.chat.id, target.id)
    except RPCError as e:
        await message.reply_text(f"{pick(GENERIC_ERROR_LINES)} (`{e}`)")
        return
    text = f"{mention_md(target.id, target.first_name)} has been kicked. Door's that way. 🔥"
    if reason:
        text += f"\n**Reason:** {reason}"
    await message.reply_text(text)


# ---------------------------------------------------------------- mute/unmute
@Client.on_message(filters.command("mute") & filters.group)
@admins_only(permission="can_restrict_members")
@bot_admin_required(permission="can_restrict_members")
async def mute_cmd(client, message):
    target = await extract_user(client, message)
    if not await _guard_target(client, message, target):
        return
    reason = reason_from_command(message, used_reply=bool(message.reply_to_message))
    try:
        await client.restrict_chat_member(message.chat.id, target.id, MUTE_PERMS)
    except RPCError as e:
        await message.reply_text(f"{pick(GENERIC_ERROR_LINES)} (`{e}`)")
        return
    text = f"{mention_md(target.id, target.first_name)} has been muted. Quiet time. 🔥"
    if reason:
        text += f"\n**Reason:** {reason}"
    await message.reply_text(text)


@Client.on_message(filters.command("unmute") & filters.group)
@admins_only(permission="can_restrict_members")
@bot_admin_required(permission="can_restrict_members")
async def unmute_cmd(client, message):
    target = await extract_user(client, message)
    if target is None:
        await message.reply_text("Who am I unmuting? Reply or give me a @username / id.")
        return
    try:
        await client.restrict_chat_member(message.chat.id, target.id, UNMUTE_PERMS)
    except RPCError as e:
        await message.reply_text(f"{pick(GENERIC_ERROR_LINES)} (`{e}`)")
        return
    await message.reply_text(f"{mention_md(target.id, target.first_name)} can speak again.")


# ---------------------------------------------------------------- timed variants
def _parse_target_duration_reason(message):
    """Handles both `/tban <duration> [reason]` (reply) and
    `/tban <target> <duration> [reason]` (no reply)."""
    used_reply = bool(message.reply_to_message)
    parts = message.text.split()[1:]
    if used_reply:
        duration = parse_duration(parts[0]) if parts else None
        reason = " ".join(parts[1:]) if len(parts) > 1 else ""
    else:
        duration = parse_duration(parts[1]) if len(parts) > 1 else None
        reason = " ".join(parts[2:]) if len(parts) > 2 else ""
    return duration, reason


@Client.on_message(filters.command("tban") & filters.group)
@admins_only(permission="can_restrict_members")
@bot_admin_required(permission="can_restrict_members")
async def tban_cmd(client, message):
    target = await extract_user(client, message)
    if not await _guard_target(client, message, target):
        return
    duration, reason = _parse_target_duration_reason(message)
    if not duration:
        await message.reply_text("Give me a duration too, like `/tban 90m` or `/tban @user 1d spamming`.")
        return
    until = datetime.now() + timedelta(seconds=duration)
    try:
        await client.ban_chat_member(message.chat.id, target.id, until_date=until)
    except RPCError as e:
        await message.reply_text(f"{pick(GENERIC_ERROR_LINES)} (`{e}`)")
        return
    text = f"{mention_md(target.id, target.first_name)} is banned until {until.strftime('%Y-%m-%d %H:%M UTC')}. 🔥"
    if reason:
        text += f"\n**Reason:** {reason}"
    await message.reply_text(text)


@Client.on_message(filters.command("tmute") & filters.group)
@admins_only(permission="can_restrict_members")
@bot_admin_required(permission="can_restrict_members")
async def tmute_cmd(client, message):
    target = await extract_user(client, message)
    if not await _guard_target(client, message, target):
        return
    duration, reason = _parse_target_duration_reason(message)
    if not duration:
        await message.reply_text("Give me a duration too, like `/tmute 30m` or `/tmute @user 2h too loud`.")
        return
    until = datetime.now() + timedelta(seconds=duration)
    try:
        await client.restrict_chat_member(message.chat.id, target.id, MUTE_PERMS, until_date=until)
    except RPCError as e:
        await message.reply_text(f"{pick(GENERIC_ERROR_LINES)} (`{e}`)")
        return
    text = f"{mention_md(target.id, target.first_name)} is muted until {until.strftime('%Y-%m-%d %H:%M UTC')}."
    if reason:
        text += f"\n**Reason:** {reason}"
    await message.reply_text(text)


# ---------------------------------------------------------------- promote/demote
@Client.on_message(filters.command(["promote", "fullpromote"]) & filters.group)
@admins_only(permission="can_promote_members")
@bot_admin_required(permission="can_promote_members")
async def promote_cmd(client, message):
    target = await extract_user(client, message)
    if target is None:
        await message.reply_text("Who am I promoting? Reply or give me a @username / id.")
        return
    full = message.command[0].lower() == "fullpromote"
    title = None
    if not message.reply_to_message and len(message.command) > 2:
        title = " ".join(message.command[2:])[:16]
    privileges = ChatPrivileges(
        can_manage_chat=True,
        can_delete_messages=True,
        can_restrict_members=True,
        can_invite_users=True,
        can_pin_messages=True,
        can_manage_video_chats=True,
        can_change_info=full,
        can_promote_members=full,
    )
    try:
        await client.promote_chat_member(message.chat.id, target.id, privileges=privileges, title=title)
    except RPCError as e:
        await message.reply_text(f"{pick(GENERIC_ERROR_LINES)} (`{e}`)")
        return
    kind = "full admin" if full else "admin"
    await message.reply_text(f"{mention_md(target.id, target.first_name)} is now {kind}. Don't make me regret it.")


@Client.on_message(filters.command("demote") & filters.group)
@admins_only(permission="can_promote_members")
@bot_admin_required(permission="can_promote_members")
async def demote_cmd(client, message):
    target = await extract_user(client, message)
    if target is None:
        await message.reply_text("Who am I demoting? Reply or give me a @username / id.")
        return
    privileges = ChatPrivileges(
        can_manage_chat=False, can_delete_messages=False, can_manage_video_chats=False,
        can_restrict_members=False, can_promote_members=False, can_change_info=False,
        can_invite_users=False, can_pin_messages=False,
    )
    try:
        await client.promote_chat_member(message.chat.id, target.id, privileges=privileges)
    except RPCError as e:
        await message.reply_text(f"{pick(GENERIC_ERROR_LINES)} (`{e}`) - I likely can't demote someone senior to me.")
        return
    await message.reply_text(f"{mention_md(target.id, target.first_name)} is back to being a regular member.")


# ---------------------------------------------------------------- pin/unpin
@Client.on_message(filters.command("pin") & filters.group)
@admins_only(permission="can_pin_messages")
@bot_admin_required(permission="can_pin_messages")
async def pin_cmd(client, message):
    if not message.reply_to_message:
        await message.reply_text("Reply to the message you want pinned.")
        return
    loud = len(message.command) > 1 and message.command[1].lower() in ("loud", "notify")
    try:
        await client.pin_chat_message(
            message.chat.id, message.reply_to_message.id, disable_notification=not loud
        )
    except RPCError as e:
        await message.reply_text(f"{pick(GENERIC_ERROR_LINES)} (`{e}`)")
        return
    await message.reply_text("Pinned. 🔥")


@Client.on_message(filters.command("unpin") & filters.group)
@admins_only(permission="can_pin_messages")
@bot_admin_required(permission="can_pin_messages")
async def unpin_cmd(client, message):
    if message.reply_to_message:
        await client.unpin_chat_message(message.chat.id, message.reply_to_message.id)
    else:
        await client.unpin_chat_message(message.chat.id)
    await message.reply_text("Unpinned.")


@Client.on_message(filters.command("unpinall") & filters.group)
@admins_only(permission="can_pin_messages")
@bot_admin_required(permission="can_pin_messages")
async def unpinall_cmd(client, message):
    try:
        await client.unpin_all_chat_messages(message.chat.id)
    except RPCError as e:
        await message.reply_text(f"{pick(GENERIC_ERROR_LINES)} (`{e}`)")
        return
    await message.reply_text("Cleared every pin in here.")


# ---------------------------------------------------------------- info
@Client.on_message(filters.command("adminlist") & filters.group)
async def adminlist_cmd(client, message):
    lines = []
    async for member in client.get_chat_members(message.chat.id, filter=ChatMembersFilter.ADMINISTRATORS):
        tag = "👑" if member.status == ChatMemberStatus.OWNER else "🔥"
        name = member.user.first_name or member.user.username or str(member.user.id)
        lines.append(f"{tag} {mention_md(member.user.id, name)}")
    if not lines:
        await message.reply_text("Couldn't fetch the admin list.")
        return
    await message.reply_text("**Admins in this chat:**\n" + "\n".join(lines))


@Client.on_message(filters.command("zombies") & filters.group)
@admins_only(permission="can_restrict_members")
@bot_admin_required(permission="can_restrict_members")
async def zombies_cmd(client, message):
    status_msg = await message.reply_text("Scanning for deleted accounts still hanging around...")
    removed = 0
    async for member in client.get_chat_members(message.chat.id, filter=ChatMembersFilter.RECENT):
        if member.user and member.user.is_deleted:
            try:
                await client.ban_chat_member(message.chat.id, member.user.id)
                await client.unban_chat_member(message.chat.id, member.user.id)
                removed += 1
            except RPCError:
                continue
    await status_msg.edit_text(f"Swept out {removed} zombie account(s). 🔥" if removed else "No zombies here - clean.")
