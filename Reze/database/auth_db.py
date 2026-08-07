"""
Live authorization state - the DB-backed half of access control (see
Reze/config.py for the env-var half). Single document so both lists
load in one round trip.
"""
from Reze.database import auth_col

_DOC_ID = "global"


async def _get_doc() -> dict:
    doc = await auth_col.find_one({"_id": _DOC_ID})
    if not doc:
        doc = {"_id": _DOC_ID, "approved_groups": [], "approved_dm_users": []}
        await auth_col.insert_one(doc)
    return doc


async def approve_group(chat_id: int):
    await auth_col.update_one({"_id": _DOC_ID}, {"$addToSet": {"approved_groups": chat_id}}, upsert=True)


async def unapprove_group(chat_id: int):
    await auth_col.update_one({"_id": _DOC_ID}, {"$pull": {"approved_groups": chat_id}}, upsert=True)


async def is_group_approved_db(chat_id: int) -> bool:
    doc = await _get_doc()
    return chat_id in doc.get("approved_groups", [])


async def approve_dm_user(user_id: int):
    await auth_col.update_one({"_id": _DOC_ID}, {"$addToSet": {"approved_dm_users": user_id}}, upsert=True)


async def unapprove_dm_user(user_id: int):
    await auth_col.update_one({"_id": _DOC_ID}, {"$pull": {"approved_dm_users": user_id}}, upsert=True)


async def is_dm_user_approved_db(user_id: int) -> bool:
    doc = await _get_doc()
    return user_id in doc.get("approved_dm_users", [])


async def list_all() -> dict:
    return await _get_doc()
