"""
/dl <url> - pulls media via yt-dlp (YouTube and most other common sites
it supports) and sends it back. Pyrofork talks MTProto directly rather
than the HTTP Bot API, so the practical upload ceiling is much higher
than the usual 50MB Bot-API limit - still, very large files can take a
while and may hit Telegram's absolute per-file cap.
"""
import os
import tempfile
import asyncio

from pyrogram import Client, filters
from pyrogram.errors import RPCError

from Reze.logger import LOGGER

MAX_BYTES = 300 * 1024 * 1024  # practical ceiling for a hobby-tier Railway deploy


def _run_ytdlp(url: str, outtmpl: str):
    import yt_dlp
    opts = {
        "format": "best[filesize<300M]/best",
        "outtmpl": outtmpl,
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
    }
    with yt_dlp.YoutubeDL(opts) as ydl:
        return ydl.extract_info(url, download=True)


@Client.on_message(filters.command(["dl", "download"]))
async def download_cmd(client, message):
    if len(message.command) < 2:
        await message.reply_text("Give me a link. `/dl <url>`")
        return
    url = message.command[1]
    status = await message.reply_text("Downloading... 🔥 (can take a moment)")

    with tempfile.TemporaryDirectory() as tmp:
        outtmpl = os.path.join(tmp, "%(title).80s.%(ext)s")
        try:
            info = await asyncio.to_thread(_run_ytdlp, url, outtmpl)
        except Exception as e:
            LOGGER.warning("yt-dlp failed for %s: %s", url, e)
            await status.edit_text(f"Couldn't download that. (`{e}`)")
            return

        files = [f for f in os.listdir(tmp) if not f.startswith(".")]
        if not files:
            await status.edit_text("Download finished but I couldn't find the resulting file.")
            return
        path = os.path.join(tmp, files[0])
        if os.path.getsize(path) > MAX_BYTES:
            await status.edit_text("That file's too large for me to send here.")
            return

        await status.edit_text("Uploading... 🔥")
        try:
            await message.reply_document(path, caption=(info or {}).get("title", "")[:1000])
            await status.delete()
        except RPCError as e:
            await status.edit_text(f"Couldn't upload that. (`{e}`)")
