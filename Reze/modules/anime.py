"""
/anime <title> - free lookup via the Jikan API (unofficial MyAnimeList
API, no key required). Given the interest in shows like Demon Slayer
and Chainsaw Man that keeps coming up, this felt like an easy win to
include for real rather than stub out.
"""
import aiohttp
from pyrogram import Client, filters

JIKAN_URL = "https://api.jikan.moe/v4/anime"


@Client.on_message(filters.command("anime"))
async def anime_cmd(client, message):
    if len(message.command) < 2:
        await message.reply_text("Usage: `/anime <title>` — e.g. `/anime chainsaw man`")
        return
    query = message.text.split(None, 1)[1]
    status = await message.reply_text("Looking that up... 🔥")

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                JIKAN_URL, params={"q": query, "limit": 1}, timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                data = await resp.json()
    except Exception:
        await status.edit_text("Couldn't reach the anime database right now. Try again shortly.")
        return

    results = data.get("data") or []
    if not results:
        await status.edit_text(f"No results for **{query}**.")
        return

    a = results[0]
    synopsis = (a.get("synopsis") or "No synopsis available.").strip()
    if len(synopsis) > 500:
        synopsis = synopsis[:500].rsplit(" ", 1)[0] + "…"

    text = (
        f"**{a.get('title', query)}**\n"
        f"⭐ {a.get('score', '?')} · 📺 {a.get('episodes', '?')} episodes · {a.get('status', '?')}\n\n"
        f"{synopsis}\n\n"
        f"[More on MyAnimeList]({a.get('url', '')})"
    )
    await status.edit_text(text, disable_web_page_preview=True)
