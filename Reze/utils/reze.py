"""
Every user-facing string funnels through here. Keeping Reze's voice in
one file means the personality can be retuned in one place instead of
hunting through 30 modules - the same lesson learned from tuning
Shinobu's tone across her whole plugin set.

Voice: warm, a little playful, quietly dangerous when crossed. Steady
and protective at the core, with a soft-smile-hiding-a-lot warmth on
the surface. 🔥🥟
"""
import random

WAKE_LINES = [
    "Reze is armed and ready~ 🔥",
]

START_PRIVATE = """\
⍣ 𝖧𝖾𝗒𝖺 {user}, 𝖱𝖾𝗓𝖾 𝗁𝖾𝗋𝖾..! 𝖨'𝗆 𝖺 𝗀𝗋𝗈𝗎𝗉 𝗆𝖺𝗇𝖺𝗀𝖾𝗆𝖾𝗇𝗍 𝖻𝗈𝗍 𝗐𝗂𝗍𝗁 𝖺 𝗌𝗈𝖿𝗍 𝗏𝗈𝗂𝖼𝖾 𝖺𝗇𝖽 𝖺 𝗌𝗁𝖺𝗋𝗉 𝖾𝖽𝗀𝖾 𝗐𝗁𝖾𝗇 𝗂𝗍'𝗌 𝗇𝖾𝖾𝖽𝖾𝖽.
──────────────────────
➛ 30+ 𝖿𝖾𝖺𝗍𝗎𝗋𝖾𝗌, 𝖿𝗋𝗈𝗆 𝗆𝗈𝖽𝖾𝗋𝖺𝗍𝗂𝗈𝗇 𝗍𝗈 𝗌𝗍𝗂𝖼𝗄𝖾𝗋𝗌 𝗍𝗈 𝗍𝗋𝖺𝗇𝗌𝗅𝖺𝗍𝗂𝗈𝗇
➛ 𝖤𝖺𝗌𝗒 𝗍𝗈 𝗎𝗌𝖾, 𝖺𝗅𝗅-𝗂𝗇-𝗈𝗇𝖾 𝖻𝗈𝗍
➛ 𝖨 𝗄𝖾𝖾𝗉 𝗒𝗈𝗎𝗋 𝗀𝗋𝗈𝗎𝗉 𝗌𝖺𝖿𝖾, 𝖺𝗇𝖽 𝗄𝖾𝖾𝗉 𝗂𝗍 𝗍𝗁𝖺𝗍 𝗐𝖺𝗒
──────────────────────
⍣ 𝖧𝗂𝗍 /help 𝗍𝗈 𝗌𝖾𝖾 𝖾𝗏𝖾𝗋𝗒𝗍𝗁𝗂𝗇𝗀 𝖨 𝖼𝖺𝗇 𝖽𝗈. 🔥"""

START_GROUP = "I'm awake~ 🔥 Poke me in PM for the full list of what I can do for {chat}."

HELP_HEADER = (
    "Hey there! My name is Reze.\n"
    "Main commands available:\n"
    "• Tap a button below for details on that module.\n"
    "• Problems? Tell our support group, I'll hear about it.\n"
    "• `/help <module>`: sends you info on that module in PM.\n"
    "• `/settings`:\n"
    "     In PM — sends your settings for every supported module.\n"
    "     In a group — redirects you to PM with that chat's settings.\n"
)

ABOUT_TEXT = """\
I'm Reze, a group management bot built to help you manage your group easily.
» I can restrict users.
» I can greet users with customizable welcome messages and even set a group's rules.
» I have an advanced anti-flood system.
» I can warn users until they reach max warns, with predefined actions such as ban, mute, kick, etc.
» I have a note keeping system, blacklists, and predetermined replies on certain keywords.
» I check for admins' permissions before executing any command, and more.
» I can turn photos, videos, GIFs and even quoted messages into stickers for your own personal pack.
» I can translate text between languages, right in the chat.

Reze's licensed under the GNU General Public License v3.0! Source is yours to read, fork, and improve.
"""

# ---- permission denials (a little variety so it doesn't feel robotic) ----
NOT_ADMIN_LINES = [
    "Not so fast — that's an admin's call, not yours. 🔥",
    "Cute try. You'll need to be an admin here first.",
    "I only take orders like that from admins of this chat.",
]

BOT_NOT_ADMIN_LINES = [
    "I don't have the muscle for that here — make me admin with the right permissions first. 🔥",
    "I can't do that until someone gives me admin rights in this chat.",
]

TARGET_IS_ADMIN_LINES = [
    "That one's an admin. Even I pick my fights carefully. 🔥",
    "I'm not touching a fellow admin — sort that out among yourselves.",
]

CANT_ACTION_OWNER = "That's the chat owner. Not even I have jurisdiction there."

GENERIC_ERROR_LINES = [
    "That didn't go the way I planned. Try again in a moment?",
    "Something slipped — mind trying that once more?",
]


def pick(lines) -> str:
    return random.choice(lines) if isinstance(lines, list) else lines
