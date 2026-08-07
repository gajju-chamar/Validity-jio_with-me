"""
Single source of truth for the /help grid - button order matches the
reference screenshots exactly (24 on page 1, 12 on page 2, 3 columns).
Each entry: (button_label, key, description_shown_when_tapped).

Status is tracked honestly in the description text itself rather than
hidden - a couple of these need a key only you can provide (imdb, ai),
and two are flagged as not included at all (cricket, anti-nsfw) because
building them for real needs a paid third-party API this bot doesn't
carry. Everything else here is real, working functionality.
"""

MODULES = [
    ("Admins", "admins",
     "Ban, unban, kick, mute, unmute, tban, tmute, promote, demote, pin, unpin, adminlist, zombies. "
     "I check permissions both ways: yours, and mine, before I touch anything."),

    ("Ai", "ai",
     "`/ai <question>` gets you a one-off answer from Grok (xAI). She'll also jump into normal "
     "conversation on her own — just @mention her or say \"reze\" anywhere in a message. Needs "
     "your own XAI_API_KEY set in the environment — without one I'll say so plainly instead of "
     "pretending to answer."),

    ("AniQuotes", "aniquotes",
     "`/aniquote` drops a random line from a small curated anime quote bank. A personal touch, not a "
     "licensed database — don't expect every quote ever written."),

    ("Anime", "anime",
     "`/anime <title>` looks up a show via the free Jikan (MyAnimeList) API — synopsis, score, episode count."),

    ("Anti Channel", "anti_channel",
     "`/antichannel on|off` — blocks messages auto-posted into the group by a linked channel."),

    ("Anti-Spam", "antiflood",
     "Same engine as Anti-Flood below — `/antiflood`, `/setflood`, `/floodmode`. Catches the same "
     "same-user message bursts either name would suggest."),

    ("Anti-nsfw", "anti_nsfw",
     "**Not included.** Real NSFW detection needs a paid vision-classification API (Sightengine, Google "
     "Vision, etc.) or a self-hosted ML model — too heavy to fake convincingly, so I'm not pretending to."),

    ("Approvals", "approvals",
     "`/approve`, `/unapprove`, `/approved` — approved users skip locks, blacklist, and antiflood entirely."),

    ("Backup", "backup",
     "`/backup` exports this chat's settings (locks, filters, notes, welcome text, etc.) as a JSON file. "
     "`/restore` (reply to that file) loads them back in — handy when migrating or recovering."),

    ("BlackList", "blacklist",
     "`/addblacklist`, `/rmblacklist`, `/blacklist`, `/blacklistmode` — auto-moderate specific words with "
     "delete, warn, mute, kick, or ban."),

    ("Control", "control",
     "`/control` — a quick settings dashboard: see and flip the chat's main toggles (locks summary, "
     "antiflood, approval mode, anti-channel) without hunting through separate commands."),

    ("Couples", "couples",
     "`/couple` picks two random active members as \"couple of the day\" — just for fun, resets daily."),

    ("Cricket", "cricket",
     "**Not included.** Live scores need a paid sports-data API with real uptime guarantees — not something "
     "worth faking with unreliable free endpoints."),

    ("Disable", "disable",
     "`/disable <cmd>`, `/enable <cmd>`, `/disabled` — turn off specific commands for non-admins in this chat."),

    ("Downloader", "downloader",
     "`/dl <link>` — downloads from YouTube and a few other common sources via yt-dlp, sends it back "
     "as a file. Large files may hit Telegram's upload limits."),

    ("Extra Funs", "fun",
     "Part of the Fun module below — `/roll`, `/slap`, `/ship`, `/8ball`, `/truth`, `/dare` and friends."),

    ("Extras", "fun",
     "Also folded into Fun below — see `/fun` for the full command list in one place."),

    ("F-Sub", "fsub",
     "`/fsub <channel>` — require members to join a channel before they can send messages here."),

    ("Filters", "filters",
     "`/filter`, `/stop`, `/filters` — auto-reply when a keyword shows up, any content type."),

    ("Fun", "fun",
     "`/roll /slap /ship /8ball /truth /dare /meme` — lightweight fun commands, no external key needed."),

    ("Greetings", "greetings",
     "`/setwelcome`, `/setgoodbye`, `/welcome on|off`, `/goodbye on|off` — with `{mention} {first} {chatname}` "
     "and similar placeholders."),

    ("Info & AFK", "afk",
     "`/afk [reason]` marks you away; I'll answer for you if someone pings you. `/info` (reply or @user) "
     "shows a profile card."),

    ("Karma", "karma",
     "Reply `+1`/`-1` (or 👍/👎) to give karma. `/karma` checks a score, `/topkarma` shows the leaderboard."),

    ("Locks", "locks",
     "`/lock`, `/unlock`, `/locks`, `/locktypes` — block stickers, links, forwards, and 15+ other content "
     "types from non-admins."),

    ("Memes", "fun",
     "Also part of Fun — `/meme` fetches a random meme."),

    ("Mentions", "mentions",
     "`/tagall [message]` pings every member (admins only, rate-limited so it doesn't itself trigger antiflood)."),

    ("Notes", "notes",
     "`/save`, `/get`, `/notes`, `/clear` — save any message type under a name, retrieve with `/get <name>` "
     "or `#<name>`."),

    ("Purges", "purges",
     "`/del`, `/purge`, `/purgefrom` + `/purgeto` — bulk message cleanup between two points."),

    ("Reporting", "reporting",
     "Reply to a message with `/report` (or say `@admin`) to quietly ping the chat's admins."),

    ("Rules", "rules",
     "`/setrules`, `/rules`, `/clearrules` — `/rules` sends the group's rules straight to PM."),

    ("Stickers", "stickers",
     "Reply to a photo, video, GIF, or sticker with `/kang` — or just send me one in PM — and it goes "
     "into your own personal pack. `/quote` (reply to text) turns that message into a quote-card sticker."),

    ("Tagger", "mentions",
     "Same engine as Mentions above — tag everyone with a custom message attached."),

    ("Telegraph", "telegraph",
     "`/telegraph` (reply to long text) posts it to graph.org and hands you back a clean shareable link."),

    ("Tools", "tools",
     "`/id`, `/json` — quick utility commands for grabbing chat/user IDs or inspecting raw message data."),

    ("Warnings", "warns",
     "`/warn`, `/warns`, `/resetwarn`, `/warnlimit`, `/warnmode` — configurable limit and action (ban/kick/mute)."),

    ("imdb", "imdb",
     "`/imdb <title>` looks up a movie or show. Needs a free OMDb API key (omdbapi.com) set as OMDB_API_KEY "
     "— without one, I'll tell you that directly instead of returning nothing."),
]

PAGE_SIZE = 24  # 8 rows x 3 columns, matching the reference layout
PAGE_1 = MODULES[:24]
PAGE_2 = MODULES[24:]

_BY_KEY = {}
for label, key, desc in MODULES:
    _BY_KEY.setdefault(key, (label, desc))


def get_description(key: str):
    return _BY_KEY.get(key)


def find_by_label(label: str):
    for l, k, d in MODULES:
        if l.lower() == label.lower():
            return k, d
    return None, None
