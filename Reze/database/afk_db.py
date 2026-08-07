import time
from Reze.database import afk_col

async def set_afk(user_id: int, reason: str = ""):
    await afk_col.update_one(
        {"user_id": user_id},
        {"$set": {"reason": reason, "since": time.time()}},
        upsert=True,
    )

async def clear_afk(user_id: int):
    await afk_col.delete_one({"user_id": user_id})

async def get_afk(user_id: int):
    return await afk_col.find_one({"user_id": user_id})
