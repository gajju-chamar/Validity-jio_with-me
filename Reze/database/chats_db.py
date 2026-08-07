"""
One document per chat_id holds every per-chat setting: locks, antiflood
config, disabled commands, welcome/goodbye/rules text, f-sub, and the
handful of small toggles the Control panel exposes. Keeping it as one
document (instead of one collection per setting) means a single round
trip loads everything a message handler needs to check.
"""
from Reze.database import chats_col

DEFAULT_LOCKS = {
    "sticker": False, "photo": False, "video": False, "gif": False,
    "url": False, "forward": False, "game": False, "location": False,
    "audio": False, "contact": False, "document": False, "poll": False,
    "voice": False, "videonote": False, "inline": False, "emoji": False,
    "bot": False,
}

DEFAULT_CHAT = {
    "title": None,
    "locks": DEFAULT_LOCKS,
    "antiflood": {"enabled": False, "limit": 8, "mode": "mute"},
    "disabled_cmds": [],
    "disabled_action": "none",  # none | delete | warn
    "welcome": {"enabled": True, "text": None, "buttons": [], "clean_old": True},
    "goodbye": {"enabled": False, "text": None},
    "rules": None,
    "warn_limit": 3,
    "warn_mode": "mute",  # ban | kick | mute
    "fsub": {"enabled": False, "channel_id": None},
    "reports_enabled": True,
    "anti_channel": False,
    "approval_mode": False,
}


async def get_chat(chat_id: int) -> dict:
    doc = await chats_col.find_one({"chat_id": chat_id})
    if not doc:
        doc = {"chat_id": chat_id, **DEFAULT_CHAT}
        await chats_col.insert_one(doc)
    else:
        # backfill any keys added to DEFAULT_CHAT after this doc was created
        changed = False
        for k, v in DEFAULT_CHAT.items():
            if k not in doc:
                doc[k] = v
                changed = True
        if changed:
            await chats_col.update_one({"chat_id": chat_id}, {"$set": doc}, upsert=True)
    return doc


async def set_chat_title(chat_id: int, title: str):
    await chats_col.update_one({"chat_id": chat_id}, {"$set": {"title": title}}, upsert=True)


async def all_chat_ids() -> list:
    return [d["chat_id"] async for d in chats_col.find({}, {"chat_id": 1})]


# ---- locks ----
async def set_lock(chat_id: int, lock_type: str, state: bool):
    await get_chat(chat_id)
    await chats_col.update_one({"chat_id": chat_id}, {"$set": {f"locks.{lock_type}": state}})


async def get_locks(chat_id: int) -> dict:
    chat = await get_chat(chat_id)
    return chat["locks"]


# ---- antiflood ----
async def set_antiflood(chat_id: int, enabled: bool = None, limit: int = None, mode: str = None):
    await get_chat(chat_id)
    updates = {}
    if enabled is not None:
        updates["antiflood.enabled"] = enabled
    if limit is not None:
        updates["antiflood.limit"] = limit
    if mode is not None:
        updates["antiflood.mode"] = mode
    if updates:
        await chats_col.update_one({"chat_id": chat_id}, {"$set": updates})


# ---- disabled commands ----
async def disable_cmd(chat_id: int, cmd: str):
    await get_chat(chat_id)
    await chats_col.update_one({"chat_id": chat_id}, {"$addToSet": {"disabled_cmds": cmd.lower()}})


async def enable_cmd(chat_id: int, cmd: str):
    await chats_col.update_one({"chat_id": chat_id}, {"$pull": {"disabled_cmds": cmd.lower()}})


async def is_cmd_disabled(chat_id: int, cmd: str) -> bool:
    chat = await get_chat(chat_id)
    return cmd.lower() in chat.get("disabled_cmds", [])


# ---- welcome / goodbye / rules ----
async def set_welcome(chat_id: int, text: str = None, enabled: bool = None, buttons: list = None):
    await get_chat(chat_id)
    updates = {}
    if text is not None:
        updates["welcome.text"] = text
    if enabled is not None:
        updates["welcome.enabled"] = enabled
    if buttons is not None:
        updates["welcome.buttons"] = buttons
    if updates:
        await chats_col.update_one({"chat_id": chat_id}, {"$set": updates})


async def set_goodbye(chat_id: int, text: str = None, enabled: bool = None):
    await get_chat(chat_id)
    updates = {}
    if text is not None:
        updates["goodbye.text"] = text
    if enabled is not None:
        updates["goodbye.enabled"] = enabled
    if updates:
        await chats_col.update_one({"chat_id": chat_id}, {"$set": updates})


async def set_rules(chat_id: int, text: str):
    await get_chat(chat_id)
    await chats_col.update_one({"chat_id": chat_id}, {"$set": {"rules": text}})


# ---- warn settings ----
async def set_warn_limit(chat_id: int, limit: int):
    await get_chat(chat_id)
    await chats_col.update_one({"chat_id": chat_id}, {"$set": {"warn_limit": limit}})


async def set_warn_mode(chat_id: int, mode: str):
    await get_chat(chat_id)
    await chats_col.update_one({"chat_id": chat_id}, {"$set": {"warn_mode": mode}})


# ---- f-sub ----
async def set_fsub(chat_id: int, enabled: bool = None, channel_id: int = None):
    await get_chat(chat_id)
    updates = {}
    if enabled is not None:
        updates["fsub.enabled"] = enabled
    if channel_id is not None:
        updates["fsub.channel_id"] = channel_id
    if updates:
        await chats_col.update_one({"chat_id": chat_id}, {"$set": updates})


# ---- misc single-flag toggles (used by /control) ----
async def set_flag(chat_id: int, field: str, value):
    await get_chat(chat_id)
    await chats_col.update_one({"chat_id": chat_id}, {"$set": {field: value}})
