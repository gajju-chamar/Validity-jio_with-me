"""
Not included. Live cricket scores need a paid sports-data API with real
uptime guarantees behind it - the free/unofficial endpoints available
aren't reliable enough to build a feature on, so this is an honest stub
rather than something that quietly returns wrong scores. The button
still exists in /help so this is documented, not hidden.
"""
from pyrogram import Client, filters


@Client.on_message(filters.command("cricket"))
async def cricket_cmd(client, message):
    await message.reply_text(
        "Cricket scores aren't included — live sports data needs a paid API with real uptime "
        "behind it, and I'd rather say that plainly than guess at scores from an unreliable free source."
    )
