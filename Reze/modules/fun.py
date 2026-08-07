import random

import aiohttp
from pyrogram import Client, filters

from Reze.utils.helpers import extract_user, mention_md

SLAP_ACTIONS = [
    "slaps {t} across the room with a folding chair 🔥",
    "smacks {t} with a very large trout",
    "sends {t} flying with a roundhouse kick",
    "throws a dumpling at {t}'s face",
]

EIGHTBALL_ANSWERS = [
    "It is certain.", "Without a doubt.", "Yes, definitely.", "Ask again later.",
    "Cannot predict now.", "Don't count on it.", "My sources say no.",
    "Very doubtful.", "Signs point to yes.", "Outlook not so good.",
]

TRUTHS = [
    "What's the pettiest reason you've ever been mad at someone?",
    "What's a lie you told that somehow became your reputation?",
    "What's the most embarrassing thing in your search history?",
    "Who in this chat would you trust with a secret, and why?",
]

DARES = [
    "Send the last photo in your gallery, no context.",
    "Type your reply using only emojis for the next 3 messages.",
    "Message someone in this chat \"I know what you did\" with no explanation.",
    "Change your name to something ridiculous for the next hour.",
]


@Client.on_message(filters.command("roll"))
async def roll_cmd(client, message):
    sides = 6
    if len(message.command) > 1 and message.command[1].isdigit():
        sides = max(2, min(1000, int(message.command[1])))
    await message.reply_text(f"🎲 Rolled a {random.randint(1, sides)} (out of {sides}).")


@Client.on_message(filters.command("slap") & filters.group)
async def slap_cmd(client, message):
    target = await extract_user(client, message)
    name = mention_md(target.id, target.first_name) if target else "themselves"
    action = random.choice(SLAP_ACTIONS).format(t=name)
    await message.reply_text(f"{mention_md(message.from_user.id, message.from_user.first_name)} {action}")


@Client.on_message(filters.command("ship") & filters.group)
async def ship_cmd(client, message):
    a = message.from_user
    b = await extract_user(client, message)
    if not b:
        await message.reply_text("Reply to someone, or give me a @username, to ship with.")
        return
    if b.id == a.id:
        await message.reply_text("Shipping yourself with yourself. Bold. 100% compatible, obviously.")
        return
    pct = random.randint(0, 100)
    bar = "█" * (pct // 10) + "░" * (10 - pct // 10)
    await message.reply_text(
        f"💘 {mention_md(a.id, a.first_name)} × {mention_md(b.id, b.first_name)}\n[{bar}] {pct}%"
    )


@Client.on_message(filters.command("8ball"))
async def eightball_cmd(client, message):
    await message.reply_text(f"🎱 {random.choice(EIGHTBALL_ANSWERS)}")


@Client.on_message(filters.command("truth"))
async def truth_cmd(client, message):
    await message.reply_text(f"🫢 **Truth:** {random.choice(TRUTHS)}")


@Client.on_message(filters.command("dare"))
async def dare_cmd(client, message):
    await message.reply_text(f"🔥 **Dare:** {random.choice(DARES)}")


@Client.on_message(filters.command("meme"))
async def meme_cmd(client, message):
    status = await message.reply_text("Fetching a meme... 🔥")
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("https://meme-api.com/gimme", timeout=aiohttp.ClientTimeout(total=8)) as resp:
                data = await resp.json()
        url = data.get("url")
        title = data.get("title", "meme")
        if not url:
            raise ValueError("no url in response")
        await status.delete()
        await message.reply_photo(url, caption=title[:200])
    except Exception:
        await status.edit_text("Couldn't fetch a meme right now — the meme API might be down. Try again shortly.")
