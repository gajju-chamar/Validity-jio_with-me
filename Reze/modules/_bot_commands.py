"""
Telegram's bot-command menu (the autocomplete that pops up typing "/" in
a chat) is meant to be a short, curated list, not every alias this bot
understands - COMMANDS.md has the full 121-command reference. This is
the "greatest hits" subset, registered once at startup via
set_bot_commands().
"""
from pyrogram.types import BotCommand

MENU_COMMANDS = [
    BotCommand("start", "Wake her up / show the intro"),
    BotCommand("help", "Full command menu"),
    BotCommand("ban", "Ban a user"),
    BotCommand("mute", "Mute a user"),
    BotCommand("kick", "Kick a user"),
    BotCommand("warn", "Warn a user"),
    BotCommand("promote", "Promote a user to admin"),
    BotCommand("lock", "Lock a content type"),
    BotCommand("unlock", "Unlock a content type"),
    BotCommand("filter", "Add a keyword auto-reply"),
    BotCommand("save", "Save a note"),
    BotCommand("get", "Retrieve a note"),
    BotCommand("setwelcome", "Set the welcome message"),
    BotCommand("rules", "Show this group's rules"),
    BotCommand("kang", "Grab media into your sticker pack"),
    BotCommand("q", "Turn a message into a quote sticker"),
    BotCommand("tr", "Translate text"),
    BotCommand("ai", "Ask Grok a question"),
    BotCommand("id", "Show chat/user IDs"),
    BotCommand("info", "Show a user's profile card"),
    BotCommand("afk", "Mark yourself away"),
    BotCommand("report", "Report a message to admins"),
    BotCommand("adminlist", "List this chat's admins"),
    BotCommand("karma", "Check a karma score"),
    BotCommand("roll", "Roll a die"),
    BotCommand("anime", "Look up an anime"),
    BotCommand("control", "Open the settings dashboard"),
]
