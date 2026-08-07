from Reze.database import stickers_col

async def get_pack(user_id: int, kind: str) -> dict:
    """kind is 'static' or 'video' - Telegram requires each sticker format
    to live in its own pack, so every user gets up to two auto-packs."""
    return await stickers_col.find_one({"user_id": user_id, "kind": kind})

async def save_pack(user_id: int, kind: str, short_name: str):
    await stickers_col.update_one(
        {"user_id": user_id, "kind": kind},
        {"$set": {"short_name": short_name, "count": 1}},
        upsert=True,
    )

async def increment_pack(user_id: int, kind: str) -> int:
    doc = await stickers_col.find_one_and_update(
        {"user_id": user_id, "kind": kind},
        {"$inc": {"count": 1}},
        return_document=True,
    )
    return doc["count"] if doc else 1
