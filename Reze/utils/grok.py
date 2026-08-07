"""
Shared caller for xAI's Grok API - one place for both the explicit /ai
command and the passive @mention/"reze" chatbot trigger to go through,
so the personality and error handling stay consistent between them.

Endpoint is OpenAI-compatible: POST https://api.x.ai/v1/chat/completions
"""
import aiohttp

from Reze.config import Config

XAI_URL = "https://api.x.ai/v1/chat/completions"

# Reze's steady, protective, quietly sharp core - fused with Grok's
# voice: witty, a little irreverent, comfortable with a blunt joke or a
# sharp opinion, doesn't take itself too seriously. Kept short because
# this is a group chat, not an essay.
GROK_SYSTEM_PROMPT = (
    "You are Reze, a Telegram group chatbot. Your personality fuses two "
    "things: Reze's steady, protective, no-nonsense core, and Grok's voice - witty, "
    "a little irreverent, quick with a joke or a blunt take, not afraid of sarcasm, "
    "doesn't take itself too seriously, and isn't shy about having an opinion. "
    "You're warm toward people you're talking with, sharp toward anyone being a problem. "
    "Reply like a real chat message: short, punchy, conversational - never an essay, "
    "never a wall of bullet points unless specifically asked. Use 🔥 sparingly, not "
    "in every message."
)


class GrokError(Exception):
    pass


async def call_grok(prompt: str, system: str = GROK_SYSTEM_PROMPT, max_tokens: int = 700) -> str:
    if not Config.XAI_API_KEY:
        raise GrokError("no_key")

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                XAI_URL,
                headers={
                    "Authorization": f"Bearer {Config.XAI_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": Config.XAI_MODEL,
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": prompt},
                    ],
                    "max_tokens": max_tokens,
                },
                timeout=aiohttp.ClientTimeout(total=30),
            ) as resp:
                data = await resp.json()
    except Exception as e:
        raise GrokError(str(e))

    if "error" in data:
        msg = data["error"]
        raise GrokError(msg.get("message", str(msg)) if isinstance(msg, dict) else str(msg))

    try:
        return data["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError, TypeError):
        raise GrokError(f"unexpected response shape: {data}")
