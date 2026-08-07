"""
Lightweight global directory of every user and chat the bot has seen.
Populated passively (see modules/_seen.py) so that @username -> id
resolution and /stats work even for users the bot hasn't admin-cached.
"""
from Reze.database import users_col

async def log_user(user_id: int, username: str = None, first_name: str = None):
    await users_col.update_one(
        {"user_id": user_id},
        {"$set": {"username": username, "first_name": first_name}},
        upsert=True,
    )

async def get_user_by_username(username: str):
    return await users_col.find_one({"username": {"$regex": f"^{username}$", "$options": "i"}})

async def total_users() -> int:
    return await users_col.count_documents({})
