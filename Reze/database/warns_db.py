from Reze.database import warns_col

async def add_warn(chat_id: int, user_id: int, reason: str, by: int) -> int:
    """Returns the user's new warn count in this chat."""
    doc = await warns_col.find_one({"chat_id": chat_id, "user_id": user_id})
    if not doc:
        doc = {"chat_id": chat_id, "user_id": user_id, "warns": []}
    doc["warns"].append({"reason": reason or "No reason given", "by": by})
    await warns_col.update_one(
        {"chat_id": chat_id, "user_id": user_id},
        {"$set": {"warns": doc["warns"]}},
        upsert=True,
    )
    return len(doc["warns"])

async def get_warns(chat_id: int, user_id: int) -> list:
    doc = await warns_col.find_one({"chat_id": chat_id, "user_id": user_id})
    return doc["warns"] if doc else []

async def reset_warns(chat_id: int, user_id: int):
    await warns_col.update_one(
        {"chat_id": chat_id, "user_id": user_id}, {"$set": {"warns": []}}, upsert=True
    )

async def remove_last_warn(chat_id: int, user_id: int) -> bool:
    doc = await warns_col.find_one({"chat_id": chat_id, "user_id": user_id})
    if not doc or not doc["warns"]:
        return False
    doc["warns"].pop()
    await warns_col.update_one({"chat_id": chat_id, "user_id": user_id}, {"$set": {"warns": doc["warns"]}})
    return True
