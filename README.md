# Reze 🔥

A Telegram group management bot — advanced moderation, a full sticker pack
builder, quote cards, translation, and 30+ modules — with a voice that's
warm on the surface and a little dangerous underneath.

```
⍣ 𝖧𝖾𝗒𝖺 Sanji, 𝖱𝖾𝗓𝖾 𝗁𝖾𝗋𝖾..! 𝖨'𝗆 𝖺𝗇 𝖠𝖽𝗏𝖺𝗇𝖼𝖾 𝖠𝖨 𝖨𝗇𝗍𝖾𝗀𝗋𝖺𝗍𝖾𝖽
𝗐𝗂𝗍𝗁 𝖬𝖾𝖽𝗂𝖺-𝖣𝗈𝗐𝗇𝗅𝗈𝖺𝖽𝖾𝗋 𝖱𝗈𝖻𝗈𝗍, 𝖨'𝗅𝗅 𝖬𝖺𝗇𝖺𝗀𝖾 𝖸𝗈𝗎𝗋 𝖦𝗋𝗈𝗎𝗉 𝖤𝖺𝗌𝗂𝗅𝗒.
```

## What's actually in here

Full command-by-command reference for group members and admins lives in
[`COMMANDS.md`](./COMMANDS.md) — this section is the high-level tour.
Bot connects but never responds to anything? Start with
[`TROUBLESHOOTING.md`](./TROUBLESHOOTING.md).

**Core moderation** — ban/mute/kick/warn (with configurable limits and
actions), locks on 15+ content types, antiflood, blacklist, approvals,
filters, notes, welcome/goodbye, rules, purges, disable-per-command,
f-sub, anti-channel.

**The flagship features** (the ones you asked about twice, so they got
the most attention):
- **Stickers** — reply `/kang` to any photo, video, GIF, sticker, or
  animation (or just send one in PM) and it lands in your own personal
  pack. Static images become WEBP stickers; video/GIF content is
  transcoded to VP9/WebM with alpha transparency, correctly sized and
  bitrate-capped to Telegram's actual limits (512px frame, 512KB static
  / 256KB video). Vector/TGS stickers are declined honestly rather than
  faked — converting Lottie data needs a renderer this bot doesn't carry.
- **Quote cards** — `/quote` (reply to any text message) renders an
  avatar + name + message bubble as a sticker, Quotly-style.
- **Translate** — `/tr <lang> <text>`, no API key needed.

**Everything else** — AI chat, anime lookup, IMDb, Telegraph posting,
a media downloader, karma, couples, fun commands, AFK, tagging, a
settings control panel, backup/restore, and more. Full list and exact
commands live in `/help` once the bot is running — the menu matches the
layout you screenshotted.

## What's honestly not included

Two modules exist as commands but don't pretend to work:
- **Cricket** — live scores need a paid sports-data API with real
  uptime behind it. Not worth building on an unreliable free endpoint.
- **Anti-NSFW** — real detection needs a paid vision-classification API
  or a self-hosted model. Both are clean extension points if you want
  to wire one in later, but neither ships here.

Two more need a key *you* provide (the bot tells you plainly if it's
missing, rather than failing silently):
- **imdb** — free key from omdbapi.com
- **ai** — your own Anthropic API key

## Setup

### 1. Telegram credentials
- `API_ID` / `API_HASH` from https://my.telegram.org
- `BOT_TOKEN` from [@BotFather](https://t.me/BotFather)
- **Important:** in BotFather, run `/setprivacy` → **Disable** for this
  bot. Filters, blacklist, antiflood, and locks all need to see every
  message, not just commands — with privacy mode on, the bot only sees
  commands and replies, and those features silently stop working.

### 2. Database
Any MongoDB connection string works — MongoDB Atlas has a free tier
that's plenty for this. Set `MONGO_URI`.

### 3. Environment
Copy `.env.sample` to `.env` and fill in the values (`OWNER_ID`, support
links, and the optional module keys). Railway reads these as env vars
directly — you don't need the `.env` file itself in production, just
set the same variables in Railway's dashboard.

### 4. Deploy on Railway
This repo builds straight from the included `Dockerfile`:
1. New Project → Deploy from GitHub repo
2. Add the environment variables from `.env.sample`
3. Railway detects the Dockerfile automatically (`railway.json` pins
   the builder explicitly, just in case)
4. Deploy — logs should show `Reze is armed and ready~ 🔥`

### 4b. Deploy on Koyeb
Koyeb works well for this bot **as long as you pick the right service type**:

1. Create Service → your GitHub repo → **Service type: Worker**, not
   *Web Service*. This is the one step that actually matters: a Web
   Service expects to bind a port and pass HTTP health checks, and this
   bot does neither — it's a background process holding a persistent
   connection to Telegram, not a web server. Picking Web Service here
   will look like a health-check failure or general flakiness, not an
   obvious "wrong setting" error.
2. Builder: Docker (uses the included `Dockerfile` as-is, no changes needed)
3. Add the environment variables from `.env.sample`
4. Deploy — same `Reze is armed and ready~ 🔥` log line confirms it's live

**If you've seen "the bot starts fine, logs look normal, but nothing ever
arrives"** on any platform: that turned out to be a real, specific bug in
this bot's own startup code (an event-loop mismatch between how the client
was constructed and how it actually ran), not a hosting-platform
limitation. It's fixed now — full writeup of what it actually was and how
it was diagnosed is in `TROUBLESHOOTING.md`, worth reading if you're
troubleshooting an older deployment or just curious.

### 5. Local development
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.sample .env   # fill in your values
python3 -m Reze
```

## Project structure

```
Reze/
├── __main__.py          # entrypoint: connects DB, starts the client
├── __init__.py           # Client instance, Smart Plugins auto-loader
├── config.py              # env-driven settings
├── logger.py
├── database/               # one file per concern (warns, notes, filters...)
├── utils/
│   ├── decorators.py        # admin/bot permission gates
│   ├── helpers.py             # user extraction, duration parsing, etc.
│   └── reze.py                  # every user-facing string lives here
└── modules/                       # one file per /help button - drop in a
                                     new file and it's auto-registered,
                                     no import list to maintain
```

Every module file under `Reze/modules/` is auto-discovered — add a new
`.py` file with `@Client.on_message(...)` handlers and it just works, the
same pattern used across the Shinobu build.

## License

GNU General Public License v3.0. If you don't already have a `LICENSE`
file in this repo, GitHub's "Create new file" → license template picker
generates the standard GPLv3 text in one click.
