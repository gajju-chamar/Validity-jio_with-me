from pyrogram import Client, filters as pf

from Reze.database.filters_db import save_filter, all_filters, delete_filter, delete_all_filters
from Reze.utils.decorators import admins_only
from Reze.utils.helpers import capture_content


@Client.on_message(pf.command("filter") & pf.group)
@admins_only(permission="can_change_info")
async def add_filter_cmd(client, message):
    if len(message.command) < 2:
        await message.reply_text(
            "Usage: `/filter <keyword> <reply>`, or reply to something with `/filter <keyword>`."
        )
        return
    keyword = message.command[1]

    if message.reply_to_message:
        text, msg_type, file_id = capture_content(message.reply_to_message)
    else:
        rest = message.text.split(None, 2)
        text = rest[2] if len(rest) > 2 else ""
        msg_type, file_id = "text", None
        if not text:
            await message.reply_text("Give the filter a reply, or reply to a message to use that instead.")
            return

    await save_filter(message.chat.id, keyword, text, msg_type, file_id)
    await message.reply_text(f"Got it — I'll reply whenever someone says **{keyword}**.")


@Client.on_message(pf.command(["stop", "removefilter"]) & pf.group)
@admins_only(permission="can_change_info")
async def remove_filter_cmd(client, message):
    if len(message.command) < 2:
        await message.reply_text("Which filter should I remove? `/stop <keyword>`")
        return
    keyword = message.command[1]
    ok = await delete_filter(message.chat.id, keyword)
    await message.reply_text(f"Removed the filter on **{keyword}**." if ok else f"No filter on **{keyword}**.")


@Client.on_message(pf.command(["filters", "listfilters"]) & pf.group)
async def list_filters_cmd(client, message):
    items = await all_filters(message.chat.id)
    if not items:
        await message.reply_text("No filters set in this chat yet.")
        return
    await message.reply_text(
        "**Active filters:**\n" + "\n".join(f"• `{f['keyword']}`" for f in items)
    )


@Client.on_message(pf.command("stopall") & pf.group)
@admins_only(permission="can_change_info")
async def stopall_cmd(client, message):
    n = await delete_all_filters(message.chat.id)
    await message.reply_text(f"Cleared all {n} filter(s).")


@Client.on_message(pf.group & pf.text, group=4)
async def trigger_filter(client, message):
    text_lower = message.text.lower()
    items = await all_filters(message.chat.id)
    for f in items:
        if f["keyword"] in text_lower:
            if f["msg_type"] == "text":
                await message.reply_text(f["reply"] or "(empty)")
            else:
                await client.send_cached_media(
                    message.chat.id, f["file_id"], caption=f.get("reply") or "",
                    reply_to_message_id=message.id,
                )
            return
