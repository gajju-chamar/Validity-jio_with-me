from Reze.database import blacklist_col

DEFAULT_MODE = "delete"  # delete | warn | mute | kick | ban

async def add_word(chat_id: int, word: str):
    await blacklist_col.update_one({"chat_id": chat_id}, {"$addToSet": {"words": word.lower()}}, upsert=True)

async def remove_word(chat_id: int, word: str):
    await blacklist_col.update_one({"chat_id": chat_id}, {"$pull": {"words": word.lower()}})

async def get_words(chat_id: int) -> list:
    doc = await blacklist_col.find_one({"chat_id": chat_id})
    return doc["words"] if doc else []

async def set_mode(chat_id: int, mode: str):
    await blacklist_col.update_one({"chat_id": chat_id}, {"$set": {"mode": mode}}, upsert=True)

async def get_mode(chat_id: int) -> str:
    doc = await blacklist_col.find_one({"chat_id": chat_id})
    return doc.get("mode", DEFAULT_MODE) if doc else DEFAULT_MODE
