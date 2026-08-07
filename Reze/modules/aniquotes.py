"""
A small curated bank of original shonen-flavored lines - not a database
of verbatim show dialogue (that's someone else's copyrighted script to
reproduce, not mine), just quotes in the spirit of the genre.
"""
import random

from pyrogram import Client, filters

QUOTES = [
    ("On resolve", "Being weak today doesn't mean you're weak tomorrow. Keep moving."),
    ("On found family", "The people who choose to stay are the ones who count as family."),
    ("On fear", "Being scared doesn't make you a coward. Fighting anyway does."),
    ("On regret", "Don't let today's hesitation become tomorrow's regret."),
    ("On strength", "Strength isn't never falling. It's who you decide to protect on the way back up."),
    ("On promises", "A promise made in a moment of weakness is still a promise."),
    ("On purpose", "Find one person worth protecting, and the rest gets easier to figure out."),
    ("On endings", "Every ending is just someone else's beginning, if you let it be."),
    ("On scars", "Scars aren't proof you lost. They're proof you were still standing after."),
    ("On patience", "Sharpen quietly. Let the results make the noise."),
]


@Client.on_message(filters.command("aniquote"))
async def aniquote_cmd(client, message):
    topic, line = random.choice(QUOTES)
    await message.reply_text(f"🔥 _{line}_\n\n— {topic}")
