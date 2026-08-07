"""
Approved users skip locks, blacklist, and antiflood enforcement entirely -
useful for trusted regulars who trip filters meant for everyone else.
"""
from pyrogram import Client, filters

from Reze.database.approvals_db import approve, unapprove, list_approved
from Reze.utils.decorators import admins_only
from Reze.utils.helpers import extract_user, mention_md


@Client.on_message(filters.command("approve") & filters.group)
@admins_only(permission="can_restrict_members")
async def approve_cmd(client, message):
    target = await extract_user(client, message)
    if target is None:
        await message.reply_text("Reply to a message, or give me a @username / id to approve.")
        return
    await approve(message.chat.id, target.id)
    await message.reply_text(f"{mention_md(target.id, target.first_name)} is approved. Locks and filters won't touch them.")


@Client.on_message(filters.command("unapprove") & filters.group)
@admins_only(permission="can_restrict_members")
async def unapprove_cmd(client, message):
    target = await extract_user(client, message)
    if target is None:
        await message.reply_text("Reply to a message, or give me a @username / id to unapprove.")
        return
    await unapprove(message.chat.id, target.id)
    await message.reply_text(f"{mention_md(target.id, target.first_name)} is back under normal rules.")


@Client.on_message(filters.command(["approved", "approvedusers"]) & filters.group)
async def approved_list_cmd(client, message):
    ids = await list_approved(message.chat.id)
    if not ids:
        await message.reply_text("Nobody's approved in this chat yet.")
        return
    lines = []
    for uid in ids[:50]:
        try:
            u = await client.get_users(uid)
            lines.append(f"• {mention_md(u.id, u.first_name)}")
        except Exception:
            lines.append(f"• `{uid}`")
    await message.reply_text("**Approved users:**\n" + "\n".join(lines))
