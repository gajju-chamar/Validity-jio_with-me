"""
/imdb <title> via OMDb - needs a free key from omdbapi.com/apikey.aspx
set as OMDB_API_KEY. Without one, says so plainly instead of failing silently.
"""
import aiohttp
from pyrogram import Client, filters

from Reze.config import Config


@Client.on_message(filters.command("imdb"))
async def imdb_cmd(client, message):
    if not Config.OMDB_API_KEY:
        await message.reply_text(
            "This needs a free OMDb API key that isn't set up yet. Grab one at "
            "omdbapi.com/apikey.aspx and set `OMDB_API_KEY` in the environment — I'll pick it "
            "up automatically once it's there."
        )
        return
    if len(message.command) < 2:
        await message.reply_text("Usage: `/imdb <title>`")
        return

    title = message.text.split(None, 1)[1]
    status = await message.reply_text("Looking that up... 🔥")
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                "https://www.omdbapi.com/",
                params={"apikey": Config.OMDB_API_KEY, "t": title},
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                data = await resp.json()
    except Exception as e:
        await status.edit_text(f"Couldn't reach OMDb right now. (`{e}`)")
        return

    if data.get("Response") == "False":
        await status.edit_text(f"No result for **{title}**. ({data.get('Error', 'not found')})")
        return

    text = (
        f"**{data.get('Title')}** ({data.get('Year')})\n"
        f"⭐ {data.get('imdbRating', '?')}/10 · {data.get('Genre', '?')} · {data.get('Runtime', '?')}\n\n"
        f"{data.get('Plot', '')}\n\n"
        f"🎬 {data.get('Director', '?')}\n"
        f"[IMDb page](https://www.imdb.com/title/{data.get('imdbID', '')})"
    )
    await status.edit_text(text, disable_web_page_preview=True)
