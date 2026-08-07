"""
Passive chat mode - Reze answers naturally when someone @mentions her
or says "reze" anywhere in a message, without needing a slash command.
Silently inactive if no XAI_API_KEY is set (no nagging in every chat -
/ai already tells you plainly if the key's missing when you actually ask).
"""
import re

from pyrogram import Client, filters
from pyrogram.enums import ChatAction
from pyrogram.errors import RPCError

from Reze.config import Config
from Reze.utils.grok import call_grok, GrokError

TRIGGER_RE = re.compile(r"\breze\b", re.IGNORECASE)
MAX_CONTEXT_CHARS = 300


@Client.on_message(filters.group & filters.text, group=8)
async def chat_trigger(client, message):
    if not Config.XAI_API_KEY:
        return
    if not message.from_user or message.from_user.is_bot:
        return

    text = message.text or ""
    bot_username = (client.me.username or "").lower()

    is_tagged = bool(bot_username) and f"@{bot_username}" in text.lower()
    says_reze = bool(TRIGGER_RE.search(text))
    if not (is_tagged or says_reze):
        return

    # strip the literal @mention so it's not part of what we send to Grok
    prompt = re.sub(rf"@{re.escape(bot_username)}", "", text, flags=re.IGNORECASE).strip() if bot_username else text
    if not prompt:
        prompt = "(someone just tagged you with nothing else - say something)"

    if message.reply_to_message and (message.reply_to_message.text or message.reply_to_message.caption):
        context = (message.reply_to_message.text or message.reply_to_message.caption)[:MAX_CONTEXT_CHARS]
        prompt = f'(replying to: "{context}")\n{prompt}'

    try:
        await client.send_chat_action(message.chat.id, ChatAction.TYPING)
    except RPCError:
        pass

    try:
        reply = await call_grok(prompt)
    except GrokError:
        return  # stay quiet on failure here - a slash command failing loudly is fine, a passive trigger spamming errors into every chat isn't

    try:
        await message.reply_text(reply[:4000])
    except RPCError:
        pass
