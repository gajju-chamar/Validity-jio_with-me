"""
/backup exports this chat's configuration (locks, antiflood, welcome/
goodbye, rules, warn settings, notes, filters, blacklist) as a JSON
file. /restore (reply to that file) loads it back in - useful when
migrating to a new group or recovering after something goes sideways.
Warn history and approvals are intentionally left out - those are
per-incident state, not configuration worth carrying between chats.
"""
import json
import os
import tempfile
from datetime import datetime, timezone

from pyrogram import Client, filters

from Reze.database.chats_db import get_chat, chats_col
from Reze.database.notes_db import list_notes, get_note, save_note
from Reze.database.filters_db import all_filters, save_filter
from Reze.database.blacklist_db import get_words, get_mode, add_word, set_mode
from Reze.utils.decorators import admins_only

EXPORT_VERSION = 1


@Client.on_message(filters.command("backup") & filters.group)
@admins_only()
async def backup_cmd(client, message):
    chat = await get_chat(message.chat.id)

    notes_data = []
    for name in await list_notes(message.chat.id):
        n = await get_note(message.chat.id, name)
        if n:
            notes_data.append({
                "name": name, "content": n["content"],
                "msg_type": n["msg_type"], "file_id": n.get("file_id"),
            })

    filters_data = [
        {"keyword": f["keyword"], "reply": f["reply"], "msg_type": f["msg_type"], "file_id": f.get("file_id")}
        for f in await all_filters(message.chat.id)
    ]

    export = {
        "reze_export_version": EXPORT_VERSION,
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "chat_title": chat.get("title"),
        "settings": {
            "locks": chat["locks"],
            "antiflood": chat["antiflood"],
            "welcome": chat["welcome"],
            "goodbye": chat["goodbye"],
            "rules": chat["rules"],
            "warn_limit": chat["warn_limit"],
            "warn_mode": chat["warn_mode"],
        },
        "notes": notes_data,
        "filters": filters_data,
        "blacklist": {"words": await get_words(message.chat.id), "mode": await get_mode(message.chat.id)},
    }

    path = os.path.join(tempfile.gettempdir(), f"reze_backup_{message.chat.id}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(export, f, indent=2, ensure_ascii=False)

    await message.reply_document(
        path, caption="Chat settings backed up. Reply to this file with `/restore` (here or elsewhere) to load it back in."
    )
    os.remove(path)


@Client.on_message(filters.command("restore") & filters.group)
@admins_only()
async def restore_cmd(client, message):
    if not message.reply_to_message or not message.reply_to_message.document:
        await message.reply_text("Reply to a Reze backup JSON file with `/restore`.")
        return

    path = await client.download_media(message.reply_to_message)
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        await message.reply_text("That doesn't look like a valid backup file.")
        return
    finally:
        if path and os.path.exists(path):
            os.remove(path)

    if data.get("reze_export_version") != EXPORT_VERSION:
        await message.reply_text("That backup is from a different version of this bot and can't be restored safely.")
        return

    settings = data.get("settings", {})
    await chats_col.update_one(
        {"chat_id": message.chat.id},
        {"$set": {
            "locks": settings.get("locks", {}),
            "antiflood": settings.get("antiflood", {}),
            "welcome": settings.get("welcome", {}),
            "goodbye": settings.get("goodbye", {}),
            "rules": settings.get("rules"),
            "warn_limit": settings.get("warn_limit", 3),
            "warn_mode": settings.get("warn_mode", "mute"),
        }},
        upsert=True,
    )

    for n in data.get("notes", []):
        await save_note(message.chat.id, n["name"], n["content"], n.get("msg_type", "text"), n.get("file_id"))
    for flt in data.get("filters", []):
        await save_filter(message.chat.id, flt["keyword"], flt["reply"], flt.get("msg_type", "text"), flt.get("file_id"))
    for w in data.get("blacklist", {}).get("words", []):
        await add_word(message.chat.id, w)
    if data.get("blacklist", {}).get("mode"):
        await set_mode(message.chat.id, data["blacklist"]["mode"])

    await message.reply_text(
        f"Restored {len(data.get('notes', []))} note(s), {len(data.get('filters', []))} filter(s), "
        f"settings, and blacklist. 🔥"
    )
