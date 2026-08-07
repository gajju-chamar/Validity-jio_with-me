from Reze.database import db

filters_col = db["filters"]

async def save_filter(chat_id: int, keyword: str, reply: str, msg_type: str = "text", file_id: str = None):
    await filters_col.update_one(
        {"chat_id": chat_id, "keyword": keyword.lower()},
        {"$set": {"reply": reply, "msg_type": msg_type, "file_id": file_id}},
        upsert=True,
    )

async def get_filter(chat_id: int, keyword: str):
    return await filters_col.find_one({"chat_id": chat_id, "keyword": keyword.lower()})

async def all_filters(chat_id: int) -> list:
    return [d async for d in filters_col.find({"chat_id": chat_id})]

async def delete_filter(chat_id: int, keyword: str) -> bool:
    r = await filters_col.delete_one({"chat_id": chat_id, "keyword": keyword.lower()})
    return r.deleted_count > 0

async def delete_all_filters(chat_id: int) -> int:
    r = await filters_col.delete_many({"chat_id": chat_id})
    return r.deleted_count
