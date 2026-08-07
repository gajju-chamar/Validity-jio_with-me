from Reze.database import db

notes_col = db["notes"]

async def save_note(chat_id: int, name: str, content: str, msg_type: str = "text", file_id: str = None):
    await notes_col.update_one(
        {"chat_id": chat_id, "name": name.lower()},
        {"$set": {"content": content, "msg_type": msg_type, "file_id": file_id}},
        upsert=True,
    )

async def get_note(chat_id: int, name: str):
    return await notes_col.find_one({"chat_id": chat_id, "name": name.lower()})

async def delete_note(chat_id: int, name: str) -> bool:
    r = await notes_col.delete_one({"chat_id": chat_id, "name": name.lower()})
    return r.deleted_count > 0

async def list_notes(chat_id: int) -> list:
    return [d["name"] async for d in notes_col.find({"chat_id": chat_id}, {"name": 1}).sort("name", 1)]
