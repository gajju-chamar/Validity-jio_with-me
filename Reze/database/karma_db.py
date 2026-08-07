from Reze.database import karma_col

async def adjust_karma(chat_id: int, user_id: int, delta: int) -> int:
    doc = await karma_col.find_one_and_update(
        {"chat_id": chat_id, "user_id": user_id},
        {"$inc": {"score": delta}},
        upsert=True,
        return_document=True,
    )
    return doc["score"]

async def get_karma(chat_id: int, user_id: int) -> int:
    doc = await karma_col.find_one({"chat_id": chat_id, "user_id": user_id})
    return doc["score"] if doc else 0

async def top_karma(chat_id: int, limit: int = 10) -> list:
    cursor = karma_col.find({"chat_id": chat_id}).sort("score", -1).limit(limit)
    return [d async for d in cursor]
