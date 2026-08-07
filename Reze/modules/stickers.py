"""
The pack builder. Reply to any photo, video, GIF, sticker, or animation
with /kang and it lands in the sender's personal pack; in PM, just
sending the media directly works too. Telegram requires static and video
stickers to live in separate sets, so each user gets up to two auto-packs
(kind='static' / kind='video') - see database/stickers_db.py.

Vector/animated (.tgs) source stickers are declined rather than faked:
converting Lottie vector data would need a proper renderer, which this
bot doesn't carry. Everything else (photo/video/gif/webm-sticker) is
fully supported and was validated end-to-end against Telegram's actual
sticker specs (512px frame, 512KB static / 256KB video caps, VP9+alpha).
"""
import os
import tempfile
import asyncio
import subprocess
from typing import Optional

from PIL import Image
from pyrogram import Client, filters
from pyrogram.errors import RPCError

from Reze.database.stickers_db import get_pack, save_pack, increment_pack
from Reze.logger import LOGGER

MAX_PACK_SIZE = 120  # conservative on purpose - Telegram's real cap has moved over time
VIDEO_SIZE_CAP = 256 * 1024
STATIC_SIZE_CAP = 512 * 1024
DEFAULT_EMOJI = "🔥"


def _short_name(user_id: int, kind: str, bot_username: str, part: int = 1) -> str:
    prefix = "s" if kind == "static" else "v"
    suffix = "" if part == 1 else f"p{part}"
    return f"{prefix}{user_id}{suffix}_by_{bot_username}"


async def _resolve_kind(message) -> Optional[str]:
    """Returns 'static', 'video', 'tgs' (unsupported), or None (no usable media)."""
    if message.photo:
        return "static"
    if message.sticker:
        if message.sticker.is_animated:
            return "tgs"
        return "video" if message.sticker.is_video else "static"
    if message.video or message.animation:
        return "video"
    if message.document:
        mt = (message.document.mime_type or "").lower()
        if mt.startswith("image/") and "webp" not in mt:
            return "static"
        if mt.startswith("video/") or mt == "image/gif":
            return "video"
    return None


def _to_static_webp(src_path: str, dst_path: str):
    img = Image.open(src_path).convert("RGBA")
    w, h = img.size
    if w >= h:
        new_w, new_h = 512, max(1, round(h * 512 / w))
    else:
        new_h, new_w = 512, max(1, round(w * 512 / h))
    img = img.resize((new_w, new_h), Image.LANCZOS)
    img.save(dst_path, format="WEBP", quality=95, method=6)
    if os.path.getsize(dst_path) > STATIC_SIZE_CAP:
        img.save(dst_path, format="WEBP", quality=78, method=6)


def _ffmpeg_encode(src_path: str, dst_path: str, bitrate_k: int) -> bool:
    cmd = [
        "ffmpeg", "-y", "-i", src_path,
        "-t", "3",
        "-vf", "scale='if(gt(iw,ih),512,-2)':'if(gt(iw,ih),-2,512)',fps=30",
        "-c:v", "libvpx-vp9", "-pix_fmt", "yuva420p", "-auto-alt-ref", "0",
        "-b:v", f"{bitrate_k}k", "-maxrate", f"{bitrate_k}k", "-bufsize", f"{bitrate_k}k",
        "-an", dst_path,
    ]
    result = subprocess.run(cmd, capture_output=True)
    return result.returncode == 0 and os.path.exists(dst_path)


def _to_video_webm(src_path: str, dst_path: str) -> bool:
    for bitrate in (600, 450, 320, 220, 150, 100):
        if _ffmpeg_encode(src_path, dst_path, bitrate) and os.path.getsize(dst_path) <= VIDEO_SIZE_CAP:
            return True
    return os.path.exists(dst_path) and os.path.getsize(dst_path) <= VIDEO_SIZE_CAP


async def _process_kang(client, trigger_message, source_message, emoji: str = None):
    user = trigger_message.from_user
    if user is None:
        return

    kind = await _resolve_kind(source_message)
    if kind is None:
        await trigger_message.reply_text("I don't see anything there I can turn into a sticker.")
        return
    if kind == "tgs":
        await trigger_message.reply_text(
            "That's an animated vector sticker (TGS) - I can't convert those yet, only static "
            "images and video/gif-based content. Everything else works though!"
        )
        return

    status = await trigger_message.reply_text("Working on it... 🔥")

    with tempfile.TemporaryDirectory() as tmp:
        try:
            src_path = await client.download_media(source_message, file_name=os.path.join(tmp, "src"))
        except RPCError as e:
            await status.edit_text(f"Couldn't download that. (`{e}`)")
            return
        if not src_path:
            await status.edit_text("Couldn't download that.")
            return

        out_path = os.path.join(tmp, "out.webp" if kind == "static" else "out.webm")
        try:
            if kind == "static":
                await asyncio.to_thread(_to_static_webp, src_path, out_path)
            else:
                ok = await asyncio.to_thread(_to_video_webm, src_path, out_path)
                if not ok:
                    await status.edit_text(
                        "Couldn't squeeze that under Telegram's 256KB video sticker cap. "
                        "Try a shorter or simpler clip."
                    )
                    return
        except Exception:
            LOGGER.exception("Sticker conversion failed")
            await status.edit_text("Conversion failed on my end. Try a different file?")
            return

        bot_username = client.me.username
        chosen_emoji = emoji or DEFAULT_EMOJI
        pack = await get_pack(user.id, kind)
        label = "Stickers" if kind == "static" else "Video Stickers"

        try:
            if pack is None:
                short_name = _short_name(user.id, kind, bot_username)
                title = f"{user.first_name}'s {label} \u00bb @{bot_username}"[:64]
                await client.create_sticker_set(
                    title=title, short_name=short_name, sticker=out_path,
                    user_id=user.id, emoji=chosen_emoji,
                )
                await save_pack(user.id, kind, short_name)
            else:
                short_name = pack["short_name"]
                count = pack.get("count", 0)
                if count >= MAX_PACK_SIZE:
                    part = count // MAX_PACK_SIZE + 1
                    short_name = _short_name(user.id, kind, bot_username, part=part)
                    title = f"{user.first_name}'s {label} #{part} \u00bb @{bot_username}"[:64]
                    await client.create_sticker_set(
                        title=title, short_name=short_name, sticker=out_path,
                        user_id=user.id, emoji=chosen_emoji,
                    )
                    await save_pack(user.id, kind, short_name)
                else:
                    await client.add_sticker_to_set(
                        set_short_name=short_name, sticker=out_path,
                        user_id=user.id, emoji=chosen_emoji,
                    )
                    await increment_pack(user.id, kind)
        except RPCError as e:
            err = str(e)
            if "PEER_ID_INVALID" in err or "BOT_MISSING" in err or "Forbidden" in err.lower():
                await status.edit_text(
                    "I need you to open a PM with me first (just hit Start there), then try again - "
                    "Telegram won't let me send you a sticker file otherwise."
                )
            else:
                await status.edit_text(f"Telegram turned that down. (`{e}`)")
            return
        except ValueError as e:
            await status.edit_text(f"Something about that pack setup went sideways. (`{e}`)")
            return

    await status.edit_text(f"Added to your pack! 🔥 [View it](https://t.me/addstickers/{short_name})")


@Client.on_message(filters.command(["kang", "steal"]))
async def kang_cmd(client, message):
    if not message.reply_to_message:
        await message.reply_text("Reply to a photo, video, GIF, or sticker with `/kang` to grab it.")
        return
    emoji = None
    if len(message.command) > 1:
        emoji = message.command[1]
    await _process_kang(client, message, message.reply_to_message, emoji=emoji)


@Client.on_message(
    filters.private & (filters.photo | filters.video | filters.animation | filters.sticker | filters.document),
    group=10,
)
async def auto_kang_in_pm(client, message):
    await _process_kang(client, message, message)


@Client.on_message(filters.command(["mypacks", "mystickers"]))
async def mypacks_cmd(client, message):
    user = message.from_user
    static = await get_pack(user.id, "static")
    video = await get_pack(user.id, "video")
    if not static and not video:
        await message.reply_text(
            "No pack yet — reply to any photo/video/GIF/sticker with `/kang` (or just send me one in PM) to start one."
        )
        return
    lines = []
    if static:
        lines.append(f"🖼 [Static pack]({_pack_url(static['short_name'])}) — {static.get('count', 1)} sticker(s)")
    if video:
        lines.append(f"🎬 [Video pack]({_pack_url(video['short_name'])}) — {video.get('count', 1)} sticker(s)")
    await message.reply_text("**Your packs:**\n" + "\n".join(lines), disable_web_page_preview=True)


def _pack_url(short_name: str) -> str:
    return f"https://t.me/addstickers/{short_name}"
