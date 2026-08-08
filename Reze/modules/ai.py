"""
/ai - explicit one-off call to Grok.

For always-on chat behavior (replying when tagged or when someone
says "reze"), see chat.py.
"""

from pyrogram import Client, filters

from Reze.config import Config
from Reze.utils.grok import call_grok, GrokError


@Client.on_message(filters.command(["ai", "ask"]))
async def ai_cmd(client, message):

    # Check whether the API key is configured
    if not Config.XAI_API_KEY:
        await message.reply_text(
            "This needs your own xAI (Grok) API key, which isn't set up yet.\n\n"
            "Get one at console.x.ai and set `XAI_API_KEY` in the environment."
        )
        return

    # Get prompt from command
    if len(message.command) > 1:
        prompt = message.text.split(None, 1)[1]

    # Or use replied-to message
    elif message.reply_to_message and message.reply_to_message.text:
        prompt = message.reply_to_message.text

    else:
        await message.reply_text(
            "Usage: `/ai <question>`\n"
            "or reply to a message with `/ai`."
        )
        return

    # Tell the user we're processing
    status = await message.reply_text("Thinking... 🔥")

    try:
        reply = await call_grok(prompt)

    except GrokError as e:
        # Don't expose unnecessary internal details
        await status.edit_text(
            f"Couldn't reach Grok right now.\n\n"
            f"`{e}`"
        )
        return

    except Exception as e:
        # Catch unexpected errors so the bot doesn't crash
        print(f"[AI] Unexpected error: {type(e).__name__}: {e}")

        await status.edit_text(
            "Something went wrong while talking to Grok."
        )
        return

    # Telegram message limit is ~4096 characters
    reply = reply.strip() if reply else "..."

    await status.edit_text(reply[:4000])
