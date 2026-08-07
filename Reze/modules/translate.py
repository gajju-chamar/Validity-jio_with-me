"""
/tr <lang_code> [text] - translates a reply or inline text. Uses
deep-translator's Google backend, which needs no API key - keeps the
Railway deploy free of an extra credential to manage.
"""
import asyncio

from pyrogram import Client, filters
from deep_translator import GoogleTranslator

# a practical subset - deep-translator supports far more; these cover the
# languages people actually ask for most in group chats
LANG_NAMES = {
    "en": "English", "hi": "Hindi", "es": "Spanish", "fr": "French",
    "de": "German", "it": "Italian", "pt": "Portuguese", "ru": "Russian",
    "ja": "Japanese", "ko": "Korean", "zh-CN": "Chinese (Simplified)",
    "ar": "Arabic", "bn": "Bengali", "ur": "Urdu", "ta": "Tamil",
    "te": "Telugu", "tr": "Turkish", "id": "Indonesian", "vi": "Vietnamese",
    "nl": "Dutch", "pl": "Polish", "uk": "Ukrainian", "th": "Thai",
}


def _translate_sync(text: str, target: str) -> str:
    return GoogleTranslator(source="auto", target=target).translate(text)


@Client.on_message(filters.command(["tr", "translate"]))
async def translate_cmd(client, message):
    if len(message.command) < 2:
        await message.reply_text(
            "Usage: `/tr <lang_code> <text>`, or reply to a message with `/tr <lang_code>`.\n"
            "e.g. `/tr hi Hello there` · `/tr ja` (as a reply)\n"
            "Common codes: " + ", ".join(f"`{c}`" for c in list(LANG_NAMES)[:10]) + " ..."
        )
        return

    target = message.command[1].lower()
    if len(message.command) > 2:
        text = message.text.split(None, 2)[2]
    elif message.reply_to_message and (message.reply_to_message.text or message.reply_to_message.caption):
        text = message.reply_to_message.text or message.reply_to_message.caption
    else:
        await message.reply_text("Give me text to translate, or reply to a message that has some.")
        return

    status = await message.reply_text("Translating... 🔥")
    try:
        result = await asyncio.to_thread(_translate_sync, text, target)
    except Exception as e:
        await status.edit_text(
            f"Couldn't translate that — check the language code is right. (`{e}`)"
        )
        return

    lang_label = LANG_NAMES.get(target, target)
    await status.edit_text(f"**Translated to {lang_label}:**\n{result}")


@Client.on_message(filters.command("trlangs"))
async def translate_langs_cmd(client, message):
    lines = [f"`{code}` — {name}" for code, name in LANG_NAMES.items()]
    await message.reply_text("**Supported language codes:**\n" + "\n".join(lines))
