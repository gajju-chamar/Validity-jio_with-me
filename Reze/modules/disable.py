"""
Lets admins turn off specific commands in their chat (e.g. disable /pin
if they don't want it used). Runs in a negative handler group so it can
veto a command before its real handler (group 0) ever sees the update.
"""
import re

from pyrogram import Client, filters, StopPropagation

from Reze.database.chats_db import disable_cmd, enable_cmd, is_cmd_disabled, get_chat
from Reze.utils.decorators import admins_only
from Reze.utils.helpers import is_exempt

# message.command is only populated as a side effect of a filters.command(...)
# check actually running against the message - this handler runs in an
# earlier group than any command handler, so we parse it ourselves instead
# of depending on that side effect.
_CMD_RE = re.compile(r"^/(\w+)(?:@\w+)?")


@Client.on_message(filters.command("disable") & filters.group)
@admins_only(permission="can_change_info")
async def disable_cmd_handler(client, message):
    if len(message.command) < 2:
        await message.reply_text("Which command should I disable? e.g. `/disable pin`")
        return
    cmd = message.command[1].lstrip("/")
    await disable_cmd(message.chat.id, cmd)
    await message.reply_text(f"`/{cmd}` is disabled for non-admins here.")


@Client.on_message(filters.command("enable") & filters.group)
@admins_only(permission="can_change_info")
async def enable_cmd_handler(client, message):
    if len(message.command) < 2:
        await message.reply_text("Which command should I re-enable? e.g. `/enable pin`")
        return
    cmd = message.command[1].lstrip("/")
    await enable_cmd(message.chat.id, cmd)
    await message.reply_text(f"`/{cmd}` is enabled again.")


@Client.on_message(filters.command(["disabled", "disabledcmds"]) & filters.group)
async def disabled_list_cmd(client, message):
    chat = await get_chat(message.chat.id)
    cmds = chat.get("disabled_cmds", [])
    if not cmds:
        await message.reply_text("No commands are disabled in this chat.")
        return
    await message.reply_text("**Disabled commands:**\n" + ", ".join(f"`/{c}`" for c in cmds))


@Client.on_message(filters.group, group=-2)
async def gate_disabled_commands(client, message):
    text = message.text or message.caption
    m = _CMD_RE.match(text) if text else None
    if not m:
        return  # not a command at all - nothing to gate
    cmd = m.group(1).lower()
    if cmd in ("disable", "enable", "disabled", "disabledcmds"):
        return  # never lock yourself out of re-enabling things
    if not await is_cmd_disabled(message.chat.id, cmd):
        return
    if message.from_user and await is_exempt(client, message.chat.id, message.from_user.id):
        return
    raise StopPropagation
