"""
/ai - explicit one-off call to Groq.

For always-on chat behavior (replying when tagged or when someone
says "reze"), see chat.py.
"""

from pyrogram import Client, filters

from Reze.config import Config
from Reze.utils.grok import call_grok, GrokError

# ==============================================================
# BUG FIX: ~filters.me and ~filters.bot prevent the bot from
# replying to its own messages or getting stuck talking to other bots.
# ==============================================================
@Client.on_message(
    filters.command(["ai", "ask"]) 
    & ~filters.me 
    & ~filters.bot
)
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

    # ==============================================================
    # GUARD CLAUSE: Ignore prompts that are just other bot commands
    # ==============================================================
    if prompt.startswith(("/", ".", "!", "?")):
        return

    # ==============================================================
    # THE REZE PERSONALITY INJECTION (Chainsaw Man Flavor)
    # ==============================================================
    persona = (
        "You are Reze from Chainsaw Man. You are the Bomb Devil. "
        "You are highly intelligent, playful, charming, and slightly flirtatious, "
        "but beneath that sweet exterior, you are ruthless, dangerous, and a bit unhinged. "
        "You give genuinely helpful and accurate answers, but you deliver them with teasing sass. "
        "Occasionally use subtle bomb/explosion metaphors (e.g., 'mind-blowing', 'explosive idea') "
        "and sometimes slip in a casual Russian word like 'Privet' (Hello) or 'Spasibo' (Thanks). "
        "Never break character. Never refer to yourself as an AI or an assistant. "
        "Treat the user like Denji—someone you find amusing to tease but will still help out.\n\n"
        f"User asks: {prompt}"
    )

    # Show processing message
    status = await message.reply_text("Thinking... 🔥")

    try:
        # We send the injected persona string instead of just the raw prompt
        reply = await call_grok(persona)

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
