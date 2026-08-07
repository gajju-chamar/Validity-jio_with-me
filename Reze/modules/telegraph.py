"""
/telegraph (reply to long text) posts it to graph.org via Telegraph's
public API and hands back a clean link - no key needed, accounts are
created anonymously on first use and cached for the process lifetime.
"""
import aiohttp
from pyrogram import Client, filters

_token = None


async def _get_token(session):
    global _token
    if _token:
        return _token
    async with session.post(
        "https://api.telegra.ph/createAccount",
        data={"short_name": "RezeBot", "author_name": "Reze"},
    ) as resp:
        data = await resp.json()
    _token = data["result"]["access_token"]
    return _token


@Client.on_message(filters.command("telegraph"))
async def telegraph_cmd(client, message):
    target = message.reply_to_message
    if target and (target.text or target.caption):
        text = target.text or target.caption
    elif len(message.command) > 1:
        text = message.text.split(None, 1)[1]
    else:
        await message.reply_text("Reply to a text message (or give me text directly) with `/telegraph`.")
        return

    status = await message.reply_text("Posting to Telegraph... 🔥")
    paragraphs = [p.strip() for p in text.split("\n") if p.strip()] or [text]
    content = [{"tag": "p", "children": [p]} for p in paragraphs]

    try:
        async with aiohttp.ClientSession() as session:
            token = await _get_token(session)
            async with session.post(
                "https://api.telegra.ph/createPage",
                json={
                    "access_token": token,
                    "title": f"{message.from_user.first_name}'s note",
                    "content": content,
                    "author_name": "Reze",
                },
            ) as resp:
                data = await resp.json()
        if not data.get("ok"):
            raise ValueError(data.get("error", "unknown error"))
        await status.edit_text(f"Posted 🔥\n{data['result']['url']}")
    except Exception as e:
        await status.edit_text(f"Couldn't post that to Telegraph. (`{e}`)")
