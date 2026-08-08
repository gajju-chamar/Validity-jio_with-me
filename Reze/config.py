"""
Central configuration. Everything is read from environment variables so the
same image runs unmodified on Railway, Docker, or a bare VPS - just change
the env vars, not the code.
"""
import os
from dotenv import load_dotenv

# On Railway/Docker, env vars are injected directly and this is a harmless
# no-op (no .env file present). Locally, this is what actually makes
# `cp .env.sample .env` + fill-in-the-blanks work as the README describes.
load_dotenv()


def _int_env(key: str, default=None):
    val = os.environ.get(key)
    if val is None or val == "":
        return default
    try:
        return int(val)
    except ValueError:
        return default

def _list_env(key: str):
    val = os.environ.get(key, "")
    result = []
    for x in val.replace(" ", "").split(","):
        x = x.strip()
        if not x:
            continue
        try:
            result.append(int(x))
        except ValueError:
            continue
    return result


class Config:
    # -- Telegram credentials (required) --
    API_ID = _int_env("API_ID")
    API_HASH = os.environ.get("API_HASH")
    BOT_TOKEN = os.environ.get("BOT_TOKEN")

    # -- Ownership --
    OWNER_ID = _int_env("OWNER_ID", 0)
    SUDO_USERS = set(_list_env("SUDO_USERS") + ([OWNER_ID] if OWNER_ID else []))

    # -- Access control --
    # Persistent allowlists edited directly via env vars (Railway dashboard
    # or .env) - survive restarts without touching the database. A group/
    # user only needs to be in EITHER this list OR the live DB-backed list
    # (see database/auth_db.py + modules/auth.py) to be authorized.
    APPROVED_GROUPS = set(_list_env("APPROVED_GROUPS"))
    ALLOWED_DM_USERS = set(_list_env("ALLOWED_DM_USERS"))

    # -- Database --
    MONGO_URI = os.environ.get("MONGO_URI")
    DB_NAME = os.environ.get("DB_NAME", "Reze")

    # -- Support links --
    SUPPORT_GROUP = os.environ.get("SUPPORT_GROUP", "https://t.me/")
    SUPPORT_CHANNEL = os.environ.get("SUPPORT_CHANNEL", "https://t.me/")

    # -- Optional --
    LOG_GROUP_ID = _int_env("LOG_GROUP_ID")
    OMDB_API_KEY = os.environ.get("OMDB_API_KEY")
    GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
    GROQ_MODEL = os.environ.get(
    "GROQ_MODEL",
    "llama-3.3-70b-versatile"
)

    # -- Bot identity / branding --
    BOT_NAME = "Reze"
    VERSION = "1.0.0"

    @classmethod
    def validate(cls):
        missing = [
            name for name, val in [
                ("API_ID", cls.API_ID),
                ("API_HASH", cls.API_HASH),
                ("BOT_TOKEN", cls.BOT_TOKEN),
                ("MONGO_URI", cls.MONGO_URI),
                ("OWNER_ID", cls.OWNER_ID or None),
            ] if not val
        ]
        if missing:
            raise SystemExit(
                f"Reze can't wake up without: {', '.join(missing)}. "
                f"Set them in your environment (see .env.sample) and try again."
            )
