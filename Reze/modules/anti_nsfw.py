"""
Not included. Real NSFW detection needs an image-classification model -
either a paid vision API (Sightengine, Google Vision, Azure Content
Moderator) or a self-hosted ML model, both well beyond what a hobby
Railway deploy carries by default. An honest stub beats a fake filter
that either lets everything through or blocks at random.
"""
from pyrogram import Client, filters

from Reze.utils.decorators import admins_only


@Client.on_message(filters.command("antinsfw") & filters.group)
@admins_only()
async def antinsfw_cmd(client, message):
    await message.reply_text(
        "NSFW detection isn't included — it needs a paid vision-classification API or a "
        "self-hosted model, neither of which this bot carries. Wiring in a provider like "
        "Sightengine or Google Vision is a clean extension point if you want to add it yourself."
    )
