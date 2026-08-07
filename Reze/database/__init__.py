from motor.motor_asyncio import AsyncIOMotorClient

from Reze.config import Config

_client = AsyncIOMotorClient(Config.MONGO_URI)
db = _client[Config.DB_NAME]

# Collections - one per concern, kept flat and explicit rather than
# nested documents, so each module's db file can be read/debugged in
# isolation (same lesson learned from iterating on Shinobu's Mongo layer).
chats_col = db["chats"]
users_col = db["users"]
warns_col = db["warns"]
notes_col = db["notes"]
filters_col = db["filters"]
blacklist_col = db["blacklist"]
approvals_col = db["approvals"]
stickers_col = db["sticker_packs"]
karma_col = db["karma"]
afk_col = db["afk"]
misc_col = db["misc"]
auth_col = db["auth"]


async def ping_database():
    await _client.admin.command("ping")
