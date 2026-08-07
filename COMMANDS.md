# Reze — Command Reference

Every command Reze understands, organized by what it does. `[reply]` means
you can reply to someone's message instead of typing their @username or ID —
that works for basically every moderation command. Commands marked **Admins**
need admin rights in that specific group; **Owner** means only the bot owner
(or someone in `SUDO_USERS`) can run it, anywhere.

Have `/setprivacy` disabled for this bot in @BotFather, or filters, blacklist,
antiflood, and locks won't see regular messages at all — only commands.

## Contents
- [Getting started](#getting-started)
- [Access control](#access-control-owner-only)
- [Moderation](#moderation-admins)
- [Warnings](#warnings-admins)
- [Locks](#locks-admins)
- [Anti-flood](#anti-flood-admins)
- [Blacklist](#blacklist-admins)
- [Filters & notes](#filters--notes)
- [Approvals](#approvals-admins)
- [Welcome, goodbye & rules](#welcome-goodbye--rules-admins)
- [Purges](#purges-admins)
- [Disabling commands](#disabling-commands-admins)
- [Anti-channel & force-subscribe](#anti-channel--force-subscribe-admins)
- [Stickers & quotes](#stickers--quotes-everyone)
- [Translate](#translate-everyone)
- [AI chat](#ai-chat-everyone)
- [Fun & games](#fun--games-everyone)
- [Anime, IMDb, Telegraph, downloads](#anime-imdb-telegraph-downloads-everyone)
- [Utilities](#utilities)
- [Backup & restore](#backup--restore-admins)
- [Not included](#not-included)

---

## Getting started

| Command | What it does |
|---|---|
| `/start` | Intro message. In DM, shows the full menu; in a group, a short line with a button to open the menu in PM. Always works, even if you're not authorized for anything else. |
| `/help` | Full command menu with tappable categories. In a group it points you to PM. `/help <module name>` (e.g. `/help Locks`) jumps straight to that category. |

## Access control (Owner only)

Reze only operates in groups the owner has approved, and DMs are limited to
`/start` for anyone who isn't separately approved. See the main `README.md`
for the full explanation — quick reference for the commands themselves:

| Command | What it does |
|---|---|
| `/authgroup [chat_id]` | Authorizes a group — run inside it, or pass an id from anywhere. |
| `/deauthgroup [chat_id]` | Revokes a group's access (only works for live-approved groups, not ones set via the `APPROVED_GROUPS` env var). |
| `/authuser [reply\|id]` | Gives a user full DM access. |
| `/deauthuser [reply\|id]` | Revokes DM access (same env-var caveat as above). |
| `/authlist` / `/authstatus` | Shows every currently-authorized group and DM user, from both the env vars and the live list. |

## Moderation (Admins)

| Command | What it does |
|---|---|
| `/ban [reply\|@user\|id] [reason]` | Bans someone from the group. |
| `/unban [reply\|@user\|id]` | Lifts a ban. |
| `/kick [reply\|@user\|id] [reason]` | Removes someone; they can rejoin via invite link. |
| `/mute [reply\|@user\|id] [reason]` | Restricts someone from sending anything. |
| `/unmute [reply\|@user\|id]` | Restores normal sending rights. |
| `/tban [duration] [reason]` *(reply)* or `/tban @user <duration> [reason]` | Temporary ban. Duration is a number + unit: `90m`, `2h`, `3d`, `1w`. |
| `/tmute [duration] [reason]` *(reply)* or `/tmute @user <duration> [reason]` | Temporary mute, same duration format. |
| `/promote [reply\|@user\|id] [title]` | Grants admin (delete, restrict, invite, pin, video chats). Custom title only works when targeting by @user/id, not reply — max 16 characters. |
| `/fullpromote [reply\|@user\|id]` | Same as `/promote`, plus the ability to change chat info and promote others. |
| `/demote [reply\|@user\|id]` | Strips admin rights back to regular member. |
| `/pin` *(reply)* `[loud]` | Pins the replied message. Add `loud` to notify members; silent by default. |
| `/unpin` *(reply, optional)* | Unpins the replied message, or the most recent pin if not replying. |
| `/unpinall` | Clears every pin in the chat. |
| `/adminlist` | Lists all admins in the chat. |
| `/zombies` | Bans and unbans every deleted account still listed as a member — a cleanup sweep. |

## Warnings (Admins)

| Command | What it does |
|---|---|
| `/warn [reply\|@user\|id] [reason]` | Adds a warning. At the limit, the configured action fires automatically and warnings reset. |
| `/warns` / `/checkwarns` *(reply, optional)* | Shows your own warnings, or someone else's. |
| `/resetwarn` / `/resetwarns` *(reply\|@user\|id)* | Clears all warnings for that person. |
| `/removewarn` / `/unwarn` *(reply\|@user\|id)* | Removes just their most recent warning. |
| `/warnlimit [number]` | Shows or sets how many warnings trigger the action (default 3). |
| `/warnmode [ban\|kick\|mute]` | Shows or sets what happens at the limit (default mute). |

## Locks (Admins)

| Command | What it does |
|---|---|
| `/lock <type>` | Blocks that content type from non-admins. |
| `/unlock <type>` | Removes the lock. |
| `/locks` | Shows what's currently locked. |
| `/locktypes` | Lists every lockable type. |

Lockable: `sticker`, `photo`, `video`, `gif`, `url`, `forward`, `game`,
`location`, `audio`, `contact`, `document`, `poll`, `voice`, `videonote`,
`inline`, `emoji` (blocks emoji-only messages), `bot` (stops non-admins from
adding other bots to the group).

## Anti-flood (Admins)

| Command | What it does |
|---|---|
| `/antiflood [on\|off]` | Shows status, or toggles it. |
| `/setflood <number>` | Sets how many messages in a row (from the same person, no one else talking in between) trigger the action. Also turns antiflood on. |
| `/floodmode <ban\|kick\|mute>` | Sets what happens to a flooder. |

## Blacklist (Admins)

| Command | What it does |
|---|---|
| `/addblacklist <word(s)>` / `/blacklist_add` | Adds word(s) — one per line or comma-separated. |
| `/rmblacklist <word>` / `/unblacklist` | Removes a word. |
| `/blacklist` / `/blacklisted` | Lists blacklisted words and the current action. |
| `/blacklistmode <delete\|warn\|mute\|kick\|ban>` | Sets what happens when someone says a blacklisted word. |

## Filters & notes

| Command | Who | What it does |
|---|---|---|
| `/filter <keyword> <reply>` *(or reply to something)* | Admins | Auto-replies whenever `keyword` appears anywhere in a message. |
| `/stop <keyword>` / `/removefilter` | Admins | Removes a filter. |
| `/filters` / `/listfilters` | Everyone | Lists active filters. |
| `/stopall` | Admins | Clears every filter in the chat. |
| `/save <name> <content>` *(or reply to something)* | Admins | Saves any message type under a name. |
| `/get <name>` / `/notes_get`, or `#name` | Everyone | Retrieves a saved note. |
| `/notes` / `/saved` | Everyone | Lists all note names. |
| `/clear <name>` / `/deletenote` | Admins | Deletes one note. |
| `/clearallnotes` | Admins | Deletes every note in the chat. |

## Approvals (Admins)

Approved users skip locks, blacklist, and antiflood entirely — for trusted
regulars who keep tripping filters meant for everyone else. (Different from
the owner-only group/DM authorization above — this is per-user, per-chat.)

| Command | What it does |
|---|---|
| `/approve [reply\|@user\|id]` | Exempts someone from automated enforcement in this chat. |
| `/unapprove [reply\|@user\|id]` | Removes the exemption. |
| `/approved` / `/approvedusers` | Lists approved users. |

## Welcome, goodbye & rules (Admins)

| Command | What it does |
|---|---|
| `/setwelcome <text>` | Sets the welcome message and turns it on. Placeholders: `{mention} {first} {last} {fullname} {username} {chatname} {id}`. |
| `/resetwelcome` | Reverts to the default welcome text. |
| `/welcome [on\|off]` | Shows status/current text, or toggles it. |
| `/setgoodbye <text>` | Sets the goodbye message and turns it on (same placeholders). |
| `/goodbye [on\|off]` | Shows status, or toggles it. |
| `/setrules <text>` | Sets the group's rules. |
| `/rules` | Sends the rules to your PM (falls back to the group if your PM is closed). |
| `/clearrules` | Clears the rules text. |

## Purges (Admins)

| Command | What it does |
|---|---|
| `/del` *(reply)* | Deletes the replied message (and your `/del`). |
| `/purge` *(reply)* | Deletes everything from the replied message up to your `/purge`. |
| `/purgefrom` *(reply)* | Marks the start point for a purge. |
| `/purgeto` *(reply)* | Deletes everything between the `/purgefrom` mark and here. |

## Disabling commands (Admins)

| Command | What it does |
|---|---|
| `/disable <command>` | Blocks non-admins from using that command in this chat. |
| `/enable <command>` | Re-enables it. |
| `/disabled` / `/disabledcmds` | Lists currently disabled commands. |

## Anti-channel & force-subscribe (Admins)

| Command | What it does |
|---|---|
| `/antichannel [on\|off]` | Blocks messages auto-posted by a linked channel (doesn't affect anonymous admins posting as the group itself). |
| `/fsub <@channel>` / `/fsub off` | Requires members to join that channel before they can post here. |

## Stickers & quotes (Everyone)

| Command | What it does |
|---|---|
| `/kang` / `/steal` *(reply to photo/video/GIF/sticker/animation)* `[emoji]` | Adds it to your personal sticker pack. Also works by just sending media directly in PM — no command needed. |
| `/mypacks` / `/mystickers` | Links to your static and video packs. |
| `/quote` *(reply to a text message)* | Turns that message into an avatar+bubble quote-card sticker. |

Static images become WEBP stickers; video/GIF/video-stickers become VP9
WebM stickers. Animated vector stickers (`.tgs`) can't be converted — Reze
will say so rather than fail silently. First time using `/kang`, you need to
have opened a PM with her at least once (a Telegram requirement, not a bot
limitation).

## Translate (Everyone)

| Command | What it does |
|---|---|
| `/tr <lang_code> <text>` / `/translate`, or `/tr <lang_code>` *(reply)* | Translates to that language. |
| `/trlangs` | Lists supported language codes. |

## AI chat (Everyone)

| Command | What it does |
|---|---|
| `/ai <question>` / `/ask` *(or reply)* | One-off question to Grok. |
| *(no command)* | Just `@mention` Reze or say **"reze"** anywhere in a message and she'll jump into the conversation. Requires `XAI_API_KEY` to be set — silently does nothing without it (so she doesn't nag every chat she's in). |

## Fun & games (Everyone)

| Command | What it does |
|---|---|
| `/roll [sides]` | Rolls a die — defaults to 6-sided. |
| `/slap [reply\|@user]` | Playful slap message. |
| `/ship [reply\|@user]` | Compatibility percentage between you and them. |
| `/8ball` | Magic 8-ball answer. |
| `/truth` | Random truth prompt. |
| `/dare` | Random dare prompt. |
| `/meme` | Fetches a random meme. |
| `/couple` | Picks two random active members as "today's couple" — same pair holds for the rest of the day. |
| `+1` / `👍` *(reply)* | Gives the replied user karma. |
| `-1` / `👎` *(reply)* | Takes karma away. |
| `/karma [reply\|@user]` | Checks a karma score. |
| `/topkarma` | Karma leaderboard. |
| `/aniquote` | Random line from a small curated anime-flavored quote bank. |

## Anime, IMDb, Telegraph, downloads (Everyone)

| Command | What it does |
|---|---|
| `/anime <title>` | Anime lookup (synopsis, score, episodes) — free, no key needed. |
| `/imdb <title>` | Movie/show lookup. Needs `OMDB_API_KEY` — tells you plainly if it's missing. |
| `/telegraph` *(reply to long text, or pass text directly)* | Posts it to graph.org and gives you the link. |
| `/dl <url>` / `/download` | Downloads from YouTube and most sites yt-dlp supports, sends it back as a file. |

## Utilities

| Command | Who | What it does |
|---|---|---|
| `/id [reply\|@user]` | Everyone | Shows the chat ID, and the target's user ID if given. |
| `/info [reply\|@user]` | Everyone | Profile card: name, ID, username, bot status. |
| `/json` *(reply, optional)* | Everyone | Dumps the raw message data — useful for debugging. |
| `/afk [reason]` | Everyone | Marks you away; Reze answers for you if someone pings or replies to you. Clears the moment you post again. |
| `/tagall [message]` / `/tag` | Admins | Pings every member, chunked to avoid tripping antiflood. |
| `/report` *(reply)* or **@admin** in a message | Everyone | Quietly pings the chat's admins about the replied message. |
| `/reports [on\|off]` | Admins | Toggles whether `/report` and `@admin` work in this chat. |
| `/control` | Admins | Dashboard of quick on/off toggles (antiflood, anti-channel, welcome, reporting) with buttons instead of separate commands. |

## Backup & restore (Admins)

| Command | What it does |
|---|---|
| `/backup` | Exports locks, antiflood, welcome/goodbye, rules, warn settings, notes, filters, and blacklist as a JSON file. |
| `/restore` *(reply to a backup file)* | Loads a backup back in — here or in a different chat. Warning history and approvals aren't included; those are per-incident state, not configuration. |

## Not included

Two commands exist and reply honestly instead of pretending to work:

| Command | Why not |
|---|---|
| `/cricket` | Live scores need a paid sports-data API with real uptime behind it. |
| `/antinsfw` | Real detection needs a paid vision-classification API or a self-hosted model — neither ships here. |

`/imdb` and `/ai` work the moment you provide your own key (`OMDB_API_KEY`,
`XAI_API_KEY`) — see `.env.sample`.
