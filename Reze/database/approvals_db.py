from Reze.database import approvals_col

async def approve(chat_id: int, user_id: int):
    await approvals_col.update_one(
        {"chat_id": chat_id}, {"$addToSet": {"users": user_id}}, upsert=True
    )

async def unapprove(chat_id: int, user_id: int):
    await approvals_col.update_one({"chat_id": chat_id}, {"$pull": {"users": user_id}})

async def is_approved(chat_id: int, user_id: int) -> bool:
    doc = await approvals_col.find_one({"chat_id": chat_id, "users": user_id})
    return doc is not None

async def list_approved(chat_id: int) -> list:
    doc = await approvals_col.find_one({"chat_id": chat_id})
    return doc["users"] if doc else []
