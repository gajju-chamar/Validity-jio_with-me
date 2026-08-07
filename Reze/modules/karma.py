from pyrogram import Client, filters

from Reze.database.karma_db import adjust_karma, get_karma, top_karma
from Reze.utils.helpers import extract_user, mention_md


@Client.on_message(filters.reply & filters.regex(r"^(\+1|👍)$") & filters.group)
async def karma_up(client, message):
    target = message.reply_to_message.from_user
    if not target or target.id == message.from_user.id or target.is_bot:
        return
    score = await adjust_karma(message.chat.id, target.id, 1)
    await message.reply_text(f"{mention_md(target.id, target.first_name)}'s karma: **{score}** ⬆️")


@Client.on_message(filters.reply & filters.regex(r"^(-1|👎)$") & filters.group)
async def karma_down(client, message):
    target = message.reply_to_message.from_user
    if not target or target.id == message.from_user.id or target.is_bot:
        return
    score = await adjust_karma(message.chat.id, target.id, -1)
    await message.reply_text(f"{mention_md(target.id, target.first_name)}'s karma: **{score}** ⬇️")


@Client.on_message(filters.command("karma") & filters.group)
async def karma_check_cmd(client, message):
    target = await extract_user(client, message) or message.from_user
    score = await get_karma(message.chat.id, target.id)
    await message.reply_text(f"{mention_md(target.id, target.first_name)}'s karma: **{score}**")


@Client.on_message(filters.command("topkarma") & filters.group)
async def topkarma_cmd(client, message):
    top = await top_karma(message.chat.id, 10)
    if not top:
        await message.reply_text("Nobody's earned karma here yet.")
        return
    lines = []
    for i, doc in enumerate(top, 1):
        try:
            u = await client.get_users(doc["user_id"])
            lines.append(f"{i}. {mention_md(u.id, u.first_name)} — **{doc['score']}**")
        except Exception:
            lines.append(f"{i}. `{doc['user_id']}` — **{doc['score']}**")
    await message.reply_text("**Karma leaderboard:**\n" + "\n".join(lines))
