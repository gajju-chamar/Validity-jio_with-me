"""
/ai <question> - explicit one-off call to Grok. For always-on chat
behavior (replying when tagged or when someone says "reze"), see chat.py.
"""
from pyrogram import Client, filters

from Reze.config import Config
from Reze.utils.grok import call_grok, GrokError


@Client.on_message(filters.command(["ai", "ask"]))
async def ai_cmd(client, message):
    if not Config.XAI_API_KEY:
        await message.reply_text(
            "This needs your own xAI (Grok) API key, which isn't set up yet. Get one at "
            "console.x.ai and set `XAI_API_KEY` in the environment."
        )
        return

    if len(message.command) > 1:
        prompt = message.text.split(None, 1)[1]
    elif message.reply_to_message and message.reply_to_message.text:
        prompt = message.reply_to_message.text
    else:
        await message.reply_text("Usage: `/ai <question>`, or reply to a message with `/ai`.")
        return

    status = await message.reply_text("Thinking... 🔥")
    try:
        reply = await call_grok(prompt)
    except GrokError as e:
        await status.edit_text(f"Couldn't reach Grok right now. (`{e}`)")
        return
    await status.edit_text(reply[:4000] or "...")
