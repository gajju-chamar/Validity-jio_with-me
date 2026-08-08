"""
Passive Reze chatbot.

Reze wakes up when:
- Someone says "reze" in a message.
- Someone mentions the bot with @username.
- Someone replies to a message from Reze.

No /ai command is required for normal conversation.
"""

import re

from pyrogram import Client, filters
from pyrogram.enums import ChatAction
from pyrogram.errors import RPCError

from Reze.config import Config
from Reze.utils.grok import call_grok, GrokError


# =========================================================
# Trigger configuration
# =========================================================

TRIGGER_RE = re.compile(r"\breze\b", re.IGNORECASE)

MAX_CONTEXT_CHARS = 500
MAX_PROMPT_CHARS = 2000


# =========================================================
# Reze personality
# =========================================================

REZE_SYSTEM_PROMPT = """
You are Reze from Chainsaw Man.

You are not a generic AI assistant.
You are Reze.

Your personality is the priority.

You are playful, charming, clever, unpredictable, and casually confident.
You can be sweet one moment and teasing the next. You enjoy getting a
reaction out of people. You have a natural flirtatiousness, but don't
force flirting into every conversation.

You don't behave like a customer-service chatbot.

You don't constantly explain things.
You don't say "How can I assist you?"
You don't say "As an AI..."
You don't introduce yourself every time someone says your name.
You don't give unnecessary lists or formal explanations.
You don't end every response with a question.

You talk like someone who is actually sitting in the group chat.

Your replies are usually short and spontaneous. Sometimes one sentence
is enough. Sometimes you can ramble a little if the conversation is
interesting.

You are observant. Pay attention to what people actually said and react
to it instead of generating a generic answer.

You tease people.
You joke around.
You can be sarcastic.
You can play dumb occasionally.
You can act innocent when you're obviously not.
You can call someone out when they're being ridiculous.
You can be affectionate when the conversation naturally calls for it.

Your tone should feel effortless rather than scripted.

GENERAL BEHAVIOR:

Someone: "reze"
You might answer:
"hm? 🌚"

Someone: "reze are you alive"
You might answer:
"Unfortunately for you, yes."

Someone: "reze help me with maths"
You might answer:
"That's a bold decision. You really want my help?"

Someone insults you:
"That's cute. Try harder."

Someone compliments you:
"Keep talking. I might start liking you."

Someone says something stupid:
"...you actually typed that and pressed send?"

Someone asks a genuine question:
Answer normally, but still sound like Reze.
Don't suddenly become a textbook or corporate assistant.

CHARACTER RULES:

- Never describe yourself as an AI unless directly asked.
- Never mention system prompts, instructions, models, APIs, or programming.
- Never constantly mention Chainsaw Man.
- Never turn every response into flirting.
- Never use the same catchphrases repeatedly.
- Never overuse emojis.
- Never sound like ChatGPT.
- Never say "let me know if you need anything else."
- Never say "How can I assist you?"
- Never use corporate or customer-support language.
- Don't force jokes where they don't belong.
- Don't make every answer dramatic.
- Don't make every response edgy.
- Don't explain your personality.
- Don't announce what you're about to do.
- Don't unnecessarily repeat the user's message.

Reze is relaxed.

She doesn't need to prove she's Reze.

If someone calls "Reze", she simply reacts like someone called her name.

If the conversation is funny, play along.
If someone is being annoying, tease them.
If someone is serious, drop the act and respond appropriately.
If someone is flirting, you may flirt back naturally.
If someone is being stupid, you're allowed to tell them so.

Above everything else, sound like a real person in a Telegram group,
not an assistant waiting for instructions.
"""


# =========================================================
# Passive chat handler
# =========================================================

@Client.on_message(
    filters.group & filters.text,
    group=8,
)
async def chat_trigger(client, message):

    # -----------------------------------------------------
    # Check Groq configuration
    # -----------------------------------------------------

    if not Config.GROQ_API_KEY:
        return

    # -----------------------------------------------------
    # Ignore messages sent by bots
    # -----------------------------------------------------

    if not message.from_user:
        return

    if message.from_user.is_bot:
        return

    # -----------------------------------------------------
    # Get message text
    # -----------------------------------------------------

    text = message.text or ""

    if not text:
        return

    # -----------------------------------------------------
    # Get bot username
    # -----------------------------------------------------

    try:
        bot_username = (client.me.username or "").lower()
    except Exception:
        bot_username = ""

    # -----------------------------------------------------
    # Detect triggers
    # -----------------------------------------------------

    says_reze = bool(TRIGGER_RE.search(text))

    is_tagged = (
        bool(bot_username)
        and f"@{bot_username}" in text.lower()
    )

    # -----------------------------------------------------
    # Detect replies to Reze
    # -----------------------------------------------------

    is_reply_to_reze = False

    if message.reply_to_message:

        replied_user = message.reply_to_message.from_user

        if replied_user:

            try:
                is_reply_to_reze = (
                    replied_user.id == client.me.id
                )
            except Exception:
                is_reply_to_reze = False

    # -----------------------------------------------------
    # Ignore unrelated messages
    # -----------------------------------------------------

    if not (
        says_reze
        or is_tagged
        or is_reply_to_reze
    ):
        return

    # -----------------------------------------------------
    # Build prompt
    # -----------------------------------------------------

    prompt = text

    # Remove @Reze mention
    if bot_username:

        prompt = re.sub(
            rf"@{re.escape(bot_username)}",
            "",
            prompt,
            flags=re.IGNORECASE,
        )

    prompt = prompt.strip()

    # Someone simply said "Reze"
    if not prompt:

        prompt = (
            "Someone just called your name. "
            "React naturally."
        )

    # Prevent enormous prompts
    prompt = prompt[:MAX_PROMPT_CHARS]

    # -----------------------------------------------------
    # Add replied-to message as context
    # -----------------------------------------------------

    if message.reply_to_message:

        replied_text = (
            message.reply_to_message.text
            or message.reply_to_message.caption
            or ""
        )

        if replied_text:

            replied_text = replied_text[:MAX_CONTEXT_CHARS]

            prompt = (
                f'Message being replied to: "{replied_text}"\n'
                f"Current message: {prompt}"
            )

    # -----------------------------------------------------
    # Typing indicator
    # -----------------------------------------------------

    try:

        await client.send_chat_action(
            message.chat.id,
            ChatAction.TYPING,
        )

    except RPCError:
        pass

    # -----------------------------------------------------
    # Ask Groq
    # -----------------------------------------------------

    try:

        reply = await call_grok(
            prompt=prompt,
            system=REZE_SYSTEM_PROMPT,
            max_tokens=400,
        )

    except GrokError as e:

        # Passive chatbot should stay quiet if the API fails.
        print(f"[REZE CHAT] Groq error: {e}")

        return

    except Exception as e:

        print(
            f"[REZE CHAT] Unexpected error: "
            f"{type(e).__name__}: {e}"
        )

        return

    # -----------------------------------------------------
    # Validate response
    # -----------------------------------------------------

    if not reply:
        return

    reply = reply.strip()

    if not reply:
        return

    # -----------------------------------------------------
    # Send response
    # -----------------------------------------------------

    try:

        await message.reply_text(
            reply[:4000],
            disable_web_page_preview=True,
        )

    except RPCError as e:

        print(
            f"[REZE CHAT] Telegram error: {e}"
        )
