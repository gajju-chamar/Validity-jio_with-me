"""
Sticker pack builder.

Reply to a photo, video, GIF, or sticker with /kang and it gets added
to the user's personal sticker pack.

Each user can have:
    - static sticker pack
    - video sticker pack

Telegram requires sticker-set short names to end with:
    _by_<bot_username>

Example:
    s123456789_by_RezeBot
    v123456789_by_RezeBot
    s123456789_p2_by_RezeBot

TGS animated/vector stickers are intentionally unsupported.
"""

import os
import re
import tempfile
import asyncio
import subprocess
from typing import Optional

from PIL import Image

from pyrogram import Client, filters
from pyrogram.errors import RPCError

from Reze.database.stickers_db import (
    get_pack,
    save_pack,
    increment_pack,
)

from Reze.logger import LOGGER


# ============================================================================
# LIMITS
# ============================================================================

MAX_PACK_SIZE = 120

VIDEO_SIZE_CAP = 256 * 1024
STATIC_SIZE_CAP = 512 * 1024

DEFAULT_EMOJI = "🔥"


# ============================================================================
# STICKER SET NAME
# ============================================================================

def _short_name(
    user_id: int,
    kind: str,
    bot_username: str,
    part: int = 1,
) -> str:
    """
    Generate a Telegram-valid sticker-set short name.

    Telegram requires:
        <name>_by_<bot_username>

    Examples:
        s123456789_by_RezeBot
        v123456789_by_RezeBot
        s123456789_p2_by_RezeBot
    """

    prefix = "s" if kind == "static" else "v"

    if part == 1:
        part_suffix = ""
    else:
        part_suffix = f"_p{part}"

    # Telegram sometimes returns usernames with @.
    bot_username = (bot_username or "").lstrip("@")

    # Keep only Telegram-safe characters.
    bot_username = re.sub(
        r"[^A-Za-z0-9_]",
        "",
        bot_username,
    )

    if not bot_username:
        bot_username = "bot"

    ending = f"_by_{bot_username}"

    base = f"{prefix}{user_id}{part_suffix}"

    # Keep the complete name within Telegram's limit.
    max_base_length = 64 - len(ending)

    if max_base_length < 1:
        max_base_length = 1

    base = base[:max_base_length]

    return f"{base}{ending}"


# ============================================================================
# MEDIA TYPE
# ============================================================================

async def _resolve_kind(message) -> Optional[str]:
    """
    Returns:

        static
        video
        tgs
        None
    """

    if message.photo:
        return "static"

    if message.sticker:

        if message.sticker.is_animated:
            return "tgs"

        if message.sticker.is_video:
            return "video"

        return "static"

    if message.video or message.animation:
        return "video"

    if message.document:

        mime_type = (
            message.document.mime_type or ""
        ).lower()

        if (
            mime_type.startswith("image/")
            and "webp" not in mime_type
        ):
            return "static"

        if (
            mime_type.startswith("video/")
            or mime_type == "image/gif"
        ):
            return "video"

    return None


# ============================================================================
# STATIC WEBP
# ============================================================================

def _to_static_webp(
    src_path: str,
    dst_path: str,
):
    image = Image.open(
        src_path
    ).convert("RGBA")

    width, height = image.size

    if width >= height:
        new_width = 512
        new_height = max(
            1,
            round(
                height * 512 / width
            ),
        )
    else:
        new_height = 512
        new_width = max(
            1,
            round(
                width * 512 / height
            ),
        )

    image = image.resize(
        (new_width, new_height),
        Image.LANCZOS,
    )

    image.save(
        dst_path,
        format="WEBP",
        quality=95,
        method=6,
    )

    # Telegram static sticker size limit.
    if os.path.getsize(dst_path) > STATIC_SIZE_CAP:

        image.save(
            dst_path,
            format="WEBP",
            quality=78,
            method=6,
        )


# ============================================================================
# FFMPEG
# ============================================================================

def _ffmpeg_encode(
    src_path: str,
    dst_path: str,
    bitrate_k: int,
) -> bool:

    command = [
        "ffmpeg",
        "-y",
        "-i",
        src_path,

        "-t",
        "3",

        "-vf",
        (
            "scale="
            "'if(gt(iw,ih),512,-2)':"
            "'if(gt(iw,ih),-2,512)',"
            "fps=30"
        ),

        "-c:v",
        "libvpx-vp9",

        "-pix_fmt",
        "yuva420p",

        "-auto-alt-ref",
        "0",

        "-b:v",
        f"{bitrate_k}k",

        "-maxrate",
        f"{bitrate_k}k",

        "-bufsize",
        f"{bitrate_k}k",

        "-an",

        dst_path,
    ]

    result = subprocess.run(
        command,
        capture_output=True,
    )

    return (
        result.returncode == 0
        and os.path.exists(dst_path)
    )


def _to_video_webm(
    src_path: str,
    dst_path: str,
) -> bool:

    for bitrate in (
        600,
        450,
        320,
        220,
        150,
        100,
    ):

        if _ffmpeg_encode(
            src_path,
            dst_path,
            bitrate,
        ):

            if (
                os.path.getsize(dst_path)
                <= VIDEO_SIZE_CAP
            ):
                return True

    return (
        os.path.exists(dst_path)
        and os.path.getsize(dst_path)
        <= VIDEO_SIZE_CAP
    )


# ============================================================================
# KANG PROCESSOR
# ============================================================================

async def _process_kang(
    client,
    trigger_message,
    source_message,
    emoji: str = None,
):

    user = trigger_message.from_user

    if user is None:
        return

    # --------------------------------------------------------------
    # Determine media type
    # --------------------------------------------------------------

    kind = await _resolve_kind(
        source_message
    )

    if kind is None:

        await trigger_message.reply_text(
            "I don't see anything there I can "
            "turn into a sticker."
        )

        return

    if kind == "tgs":

        await trigger_message.reply_text(
            "That's an animated vector sticker (TGS). "
            "I can't convert those yet. Static images "
            "and video/GIF stickers work though."
        )

        return

    status = await trigger_message.reply_text(
        "Working on it... 🔥"
    )

    # --------------------------------------------------------------
    # Temporary files
    # --------------------------------------------------------------

    with tempfile.TemporaryDirectory() as tmp:

        # ----------------------------------------------------------
        # Download source
        # ----------------------------------------------------------

        try:

            src_path = await client.download_media(
                source_message,
                file_name=os.path.join(
                    tmp,
                    "src",
                ),
            )

        except RPCError as exc:

            await status.edit_text(
                f"Couldn't download that. (`{exc}`)"
            )

            return

        if not src_path:

            await status.edit_text(
                "Couldn't download that."
            )

            return

        # ----------------------------------------------------------
        # Convert
        # ----------------------------------------------------------

        if kind == "static":

            out_path = os.path.join(
                tmp,
                "out.webp",
            )

        else:

            out_path = os.path.join(
                tmp,
                "out.webm",
            )

        try:

            if kind == "static":

                await asyncio.to_thread(
                    _to_static_webp,
                    src_path,
                    out_path,
                )

            else:

                success = await asyncio.to_thread(
                    _to_video_webm,
                    src_path,
                    out_path,
                )

                if not success:

                    await status.edit_text(
                        "Couldn't squeeze that under "
                        "Telegram's 256KB video sticker cap. "
                        "Try a shorter or simpler clip."
                    )

                    return

        except Exception:

            LOGGER.exception(
                "Sticker conversion failed"
            )

            await status.edit_text(
                "Conversion failed on my end. "
                "Try a different file?"
            )

            return

        # ----------------------------------------------------------
        # Bot username
        # ----------------------------------------------------------

        try:
            me = await client.get_me()
            bot_username = me.username
        except Exception:

            bot_username = None

        if not bot_username:

            await status.edit_text(
                "I couldn't determine my username, "
                "so Telegram won't let me create the pack."
            )

            return

        # ----------------------------------------------------------
        # Emoji
        # ----------------------------------------------------------

        chosen_emoji = (
            emoji
            or DEFAULT_EMOJI
        )

        # ----------------------------------------------------------
        # Existing pack
        # ----------------------------------------------------------

        pack = await get_pack(
            user.id,
            kind,
        )

        label = (
            "Stickers"
            if kind == "static"
            else "Video Stickers"
        )

        short_name = None

        try:

            # ======================================================
            # CREATE FIRST PACK
            # ======================================================

            if pack is None:

                short_name = _short_name(
                    user.id,
                    kind,
                    bot_username,
                )

                title = (
                    f"{user.first_name}'s "
                    f"{label} » @{bot_username}"
                )[:64]

                LOGGER.info(
                    "Creating sticker pack | "
                    "user=%s | kind=%s | short_name=%s",
                    user.id,
                    kind,
                    short_name,
                )

                await client.create_sticker_set(
                    title=title,
                    short_name=short_name,
                    sticker=out_path,
                    user_id=user.id,
                    emoji=chosen_emoji,
                )

                await save_pack(
                    user.id,
                    kind,
                    short_name,
                )

            # ======================================================
            # PACK EXISTS
            # ======================================================

            else:

                short_name = pack.get(
                    "short_name"
                )

                count = pack.get(
                    "count",
                    0,
                )

                # --------------------------------------------------
                # Existing pack is full
                # --------------------------------------------------

                if count >= MAX_PACK_SIZE:

                    part = (
                        count // MAX_PACK_SIZE
                    ) + 1

                    short_name = _short_name(
                        user.id,
                        kind,
                        bot_username,
                        part=part,
                    )

                    title = (
                        f"{user.first_name}'s "
                        f"{label} #{part} "
                        f"» @{bot_username}"
                    )[:64]

                    LOGGER.info(
                        "Creating sticker pack part | "
                        "user=%s | kind=%s | part=%s | short_name=%s",
                        user.id,
                        kind,
                        part,
                        short_name,
                    )

                    await client.create_sticker_set(
                        title=title,
                        short_name=short_name,
                        sticker=out_path,
                        user_id=user.id,
                        emoji=chosen_emoji,
                    )

                    await save_pack(
                        user.id,
                        kind,
                        short_name,
                    )

                # --------------------------------------------------
                # Add to existing pack
                # --------------------------------------------------

                else:

                    if not short_name:

                        await status.edit_text(
                            "Your saved sticker pack is missing "
                            "its Telegram name. You'll need to "
                            "start a new pack."
                        )

                        return

                    LOGGER.info(
                        "Adding sticker | "
                        "user=%s | kind=%s | pack=%s",
                        user.id,
                        kind,
                        short_name,
                    )

                    await client.add_sticker_to_set(
                        set_short_name=short_name,
                        sticker=out_path,
                        user_id=user.id,
                        emoji=chosen_emoji,
                    )

                    await increment_pack(
                        user.id,
                        kind,
                    )

        # ==========================================================
        # TELEGRAM ERRORS
        # ==========================================================

        except RPCError as exc:

            error = str(exc)

            LOGGER.error(
                "Telegram sticker operation failed | "
                "user=%s | kind=%s | pack=%s | error=%s",
                user.id,
                kind,
                short_name,
                error,
            )

            if "STICKERSET_INVALID" in error:

                await status.edit_text(
                    "Telegram rejected the sticker pack.\n\n"
                    "Your saved pack appears to be invalid "
                    "or was created under an old pack name. "
                    "Delete/reset that saved pack and try "
                    "`/kang` again."
                )

            elif (
                "PEER_ID_INVALID" in error
                or "BOT_MISSING" in error
                or "Forbidden" in error.lower()
            ):

                await status.edit_text(
                    "I need you to open a PM with me first "
                    "(just hit Start there), then try again. "
                    "Telegram won't let me create the sticker "
                    "pack otherwise."
                )

            elif "SHORT_NAME_INVALID" in error:

                await status.edit_text(
                    "Telegram rejected the sticker-pack name. "
                    "Check the bot username and try again."
                )

            elif "STICKER_PNG_NOPNG" in error:

                await status.edit_text(
                    "Telegram rejected the sticker file format."
                )

            elif "STICKER_VIDEO_NOWEBM" in error:

                await status.edit_text(
                    "Telegram rejected the video sticker format."
                )

            else:

                await status.edit_text(
                    f"Telegram turned that down. (`{exc}`)"
                )

            return

        except ValueError as exc:

            LOGGER.exception(
                "Sticker pack configuration error"
            )

            await status.edit_text(
                f"Something about that pack setup "
                f"went sideways. (`{exc}`)"
            )

            return

    # --------------------------------------------------------------
    # Success
    # --------------------------------------------------------------

    pack_url = _pack_url(
        short_name
    )

    await status.edit_text(
        f"Added to your pack! 🔥\n\n"
        f"[Open the pack]({pack_url})",
        disable_web_page_preview=True,
    )


# ============================================================================
# /kang
# ============================================================================

@Client.on_message(
    filters.command(
        ["kang", "steal"]
    )
)
async def kang_cmd(
    client,
    message,
):

    if not message.reply_to_message:

        await message.reply_text(
            "Reply to a photo, video, GIF, "
            "or sticker with `/kang` to grab it."
        )

        return

    custom_emoji = None

    if len(message.command) > 1:

        custom_emoji = (
            message.command[1]
        )

    await _process_kang(
        client,
        message,
        message.reply_to_message,
        emoji=custom_emoji,
    )


# ============================================================================
# Automatic PM kang
# ============================================================================

@Client.on_message(
    filters.private
    & (
        filters.photo
        | filters.video
        | filters.animation
        | filters.sticker
        | filters.document
    ),
    group=10,
)
async def auto_kang_in_pm(
    client,
    message,
):

    await _process_kang(
        client,
        message,
        message,
    )


# ============================================================================
# Pack URL
# ============================================================================

def _pack_url(
    short_name: str,
) -> str:

    return (
        f"https://t.me/addstickers/"
        f"{short_name}"
    )


# ============================================================================
# /mypacks
# ============================================================================

@Client.on_message(
    filters.command(
        ["mypacks", "mystickers"]
    )
)
async def mypacks_cmd(
    client,
    message,
):

    user = message.from_user

    if user is None:
        return

    static = await get_pack(
        user.id,
        "static",
    )

    video = await get_pack(
        user.id,
        "video",
    )

    if not static and not video:

        await message.reply_text(
            "No pack yet — reply to any "
            "photo/video/GIF/sticker with `/kang` "
            "(or just send me one in PM) to start one."
        )

        return

    lines = []

    if static:

        static_name = static.get(
            "short_name"
        )

        if static_name:

            lines.append(
                f"🖼 [Static pack]"
                f"({_pack_url(static_name)})"
                f" — {static.get('count', 1)} sticker(s)"
            )

    if video:

        video_name = video.get(
            "short_name"
        )

        if video_name:

            lines.append(
                f"🎬 [Video pack]"
                f"({_pack_url(video_name)})"
                f" — {video.get('count', 1)} sticker(s)"
            )

    if not lines:

        await message.reply_text(
            "Your saved pack information looks incomplete."
        )

        return

    await message.reply_text(
        "**Your packs:**\n"
        + "\n".join(lines),
        disable_web_page_preview=True,
    )
