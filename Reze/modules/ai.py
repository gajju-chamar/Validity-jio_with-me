"""
/ai - explicit one-off call to Groq.

For always-on chat behavior (replying when tagged or when someone
says "reze"), see chat.py.
"""

from pyrogram import Client, filters

from Reze.config import Config
from Reze.utils.grok import call_grok, GrokError


@Client.on_message(filters.command(["ai", "ask"]))
async def ai_cmd(client, message):

    # Check whether the Groq API key is configured
    if not Config.GROQ_API_KEY:
        await message.reply_text(
            "This needs a Groq API key, which isn't set up yet.\n\n"
            "Get one from console.groq.com and set "
            "`GROQ_API_KEY` in the environment."
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

    # Show processing message
    status = await message.reply_text("Thinking... 🔥")

    try:
        reply = await call_grok(prompt)

    except GrokError as e:
        await status.edit_text(
            f"Couldn't reach Groq right now.\n\n"
            f"`{e}`"
        )
        return

    except Exception as e:
        print(
            f"[AI] Unexpected error: "
            f"{type(e).__name__}: {e}"
        )

        await status.edit_text(
            "Something went wrong while talking to Groq."
        )
        return

    # Telegram messages have a ~4096 character limit
    reply = reply.strip() if reply else "..."

    await status.edit_text(reply[:4000])
