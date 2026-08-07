from pyrogram import Client, filters
from pyrogram.enums import ChatType

from Reze.utils.helpers import extract_user, mention_md


@Client.on_message(filters.command("id"))
async def id_cmd(client, message):
    lines = [f"**Chat ID:** `{message.chat.id}`"]
    target = await extract_user(client, message)
    if target:
        lines.append(f"**{target.first_name}'s ID:** `{target.id}`")
    elif message.chat.type == ChatType.PRIVATE:
        lines.append(f"**Your ID:** `{message.from_user.id}`")
    await message.reply_text("\n".join(lines))


@Client.on_message(filters.command("json"))
async def json_cmd(client, message):
    target = message.reply_to_message or message
    dump = str(target)
    if len(dump) > 3500:
        with open("/tmp/message.json", "w") as f:
            f.write(dump)
        await message.reply_document("/tmp/message.json", caption="That message was too big to paste inline.")
        return
    await message.reply_text(f"```json\n{dump}\n```")


@Client.on_message(filters.command("info"))
async def info_cmd(client, message):
    target = await extract_user(client, message) or message.from_user
    if target is None:
        await message.reply_text("Reply to someone, give me a @username, or just ask about yourself in PM.")
        return
    try:
        full = await client.get_users(target.id)
    except Exception:
        full = target
    lines = [
        f"**{mention_md(full.id, full.first_name)}**",
        f"**ID:** `{full.id}`",
        f"**Username:** @{full.username}" if full.username else "**Username:** none",
        f"**Bot:** {'yes' if full.is_bot else 'no'}",
    ]
    await message.reply_text("\n".join(lines))
