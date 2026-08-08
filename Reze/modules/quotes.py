"""
/q - Render a replied text message as a quote sticker.

Formatting:
- NotoSans Regular
- NotoSans Bold
- NotoSans Italic
- NotoSans BoldItalic
- Noto Color Emoji

Fonts are bundled inside:
    Reze/assets/fonts/
"""

import os
import io
import asyncio
import tempfile

import emoji
from PIL import Image, ImageDraw, ImageFont

from pyrogram import Client, filters
from pyrogram.errors import RPCError


# ============================================================================
# FONTS
# ============================================================================

FONT_DIR = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__),
        "..",
        "assets",
        "fonts",
    )
)

FONT_REG = os.path.join(
    FONT_DIR,
    "NotoSans-Regular.ttf",
)

FONT_BOLD = os.path.join(
    FONT_DIR,
    "NotoSans-Bold.ttf",
)

FONT_ITALIC = os.path.join(
    FONT_DIR,
    "NotoSans-Italic.ttf",
)

FONT_BOLD_ITALIC = os.path.join(
    FONT_DIR,
    "NotoSans-BoldItalic.ttf",
)

# Docker provides this one through fonts-noto-color-emoji.
EMOJI_FONT = "/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf"


def _font(path, size):
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"Quote font not found: {path}"
        )

    return ImageFont.truetype(path, size)


# ============================================================================
# SETTINGS
# ============================================================================

MAX_QUOTE_CHARS = 320

W = 512

# Existing quote design
BUBBLE_X = 88
BUBBLE_RIGHT = 500
BUBBLE_TOP = 20
BUBBLE_RADIUS = 18

BUBBLE_PAD_X = 17
BUBBLE_PAD_TOP = 12
BUBBLE_PAD_BOTTOM = 14

AVATAR_SIZE = 68
AVATAR_X = 8

NAME_SIZE = 22
TEXT_SIZE = 26

LINE_SPACING = 5

# Requested background.
BACKGROUND = (25, 20, 41, 255)

# Message bubble.
BUBBLE = (25, 20, 41, 255)

TEXT_COLOR = (242, 240, 246, 255)


# ============================================================================
# USER COLOURS
# ============================================================================

ACCENTS = [
    (90, 155, 225),
    (210, 115, 105),
    (115, 180, 130),
    (205, 155, 70),
    (175, 110, 205),
    (90, 180, 190),
    (220, 125, 160),
]


def _accent_for(user_id: int):
    return ACCENTS[user_id % len(ACCENTS)]


# ============================================================================
# AVATAR
# ============================================================================

def _fallback_avatar(user):
    size = 200
    accent = _accent_for(user.id)

    img = Image.new(
        "RGBA",
        (size, size),
        accent + (255,),
    )

    draw = ImageDraw.Draw(img)

    initial_source = (
        user.first_name
        or user.username
        or "?"
    )

    initial = initial_source[0].upper()

    font = _font(
        FONT_BOLD,
        96,
    )

    bbox = draw.textbbox(
        (0, 0),
        initial,
        font=font,
    )

    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]

    draw.text(
        (
            (size - tw) / 2 - bbox[0],
            (size - th) / 2 - bbox[1],
        ),
        initial,
        font=font,
        fill=(255, 255, 255, 255),
    )

    return img


def _circle_avatar(img, size):
    img = img.convert("RGBA")

    w, h = img.size

    if w != h:
        side = min(w, h)

        left = (w - side) // 2
        top = (h - side) // 2

        img = img.crop(
            (
                left,
                top,
                left + side,
                top + side,
            )
        )

    img = img.resize(
        (size, size),
        Image.LANCZOS,
    )

    mask = Image.new(
        "L",
        (size, size),
        0,
    )

    ImageDraw.Draw(mask).ellipse(
        (0, 0, size - 1, size - 1),
        fill=255,
    )

    out = Image.new(
        "RGBA",
        (size, size),
        (0, 0, 0, 0),
    )

    out.paste(
        img,
        (0, 0),
        mask,
    )

    return out


# ============================================================================
# TELEGRAM FORMATTING
# ============================================================================

def _utf16_to_py_index(text, target_offset):
    """
    Telegram entity offsets are UTF-16 offsets.

    Python strings use Unicode code points, so convert Telegram's
    offset into a Python string index.
    """

    units = 0

    for i, char in enumerate(text):

        if units >= target_offset:
            return i

        units += len(
            char.encode("utf-16-le")
        ) // 2

    return len(text)


def _entity_ranges(message):
    text = (
        message.text
        or message.caption
        or ""
    )

    entities = (
        message.entities
        or message.caption_entities
        or []
    )

    ranges = []

    for entity in entities:

        entity_type = str(
            getattr(entity, "type", "")
        ).lower()

        if entity_type not in {
            "bold",
            "italic",
            "bold_italic",
        }:
            continue

        offset = getattr(
            entity,
            "offset",
            0,
        )

        length = getattr(
            entity,
            "length",
            0,
        )

        start = _utf16_to_py_index(
            text,
            offset,
        )

        end = _utf16_to_py_index(
            text,
            offset + length,
        )

        ranges.append(
            (
                start,
                end,
                entity_type,
            )
        )

    return ranges


def _style_at(index, ranges):
    bold = False
    italic = False

    for start, end, entity_type in ranges:

        if not (
            start <= index < end
        ):
            continue

        if entity_type in {
            "bold",
            "bold_italic",
        }:
            bold = True

        if entity_type in {
            "italic",
            "bold_italic",
        }:
            italic = True

    return bold, italic


def _font_for(index, ranges, size):
    bold, italic = _style_at(
        index,
        ranges,
    )

    if bold and italic:
        return _font(
            FONT_BOLD_ITALIC,
            size,
        )

    if bold:
        return _font(
            FONT_BOLD,
            size,
        )

    if italic:
        return _font(
            FONT_ITALIC,
            size,
        )

    return _font(
        FONT_REG,
        size,
    )


# ============================================================================
# EMOJI
# ============================================================================

def _emoji_ranges(text):
    try:
        return emoji.emoji_list(text)
    except Exception:
        return []


def _emoji_at(index, emoji_ranges):
    for item in emoji_ranges:

        start = item["match_start"]
        end = item["match_end"]

        if start == index:
            return (
                end,
                item["emoji"],
            )

    return None


def _emoji_font(size):
    if not os.path.exists(EMOJI_FONT):
        return None

    try:
        return ImageFont.truetype(
            EMOJI_FONT,
            size,
        )
    except Exception:
        return None


# ============================================================================
# TEXT MEASUREMENT
# ============================================================================

def _measure(
    draw,
    text,
    start_index,
    ranges,
    size,
):
    x = 0

    emoji_ranges = _emoji_ranges(text)
    efont = _emoji_font(size)

    i = 0

    while i < len(text):

        found = _emoji_at(
            i,
            emoji_ranges,
        )

        if found and efont:

            end, value = found

            try:
                bbox = draw.textbbox(
                    (0, 0),
                    value,
                    font=efont,
                )

                width = bbox[2] - bbox[0]

                x += max(
                    width,
                    size,
                )

                i = end
                continue

            except Exception:
                pass

        char = text[i]

        font = _font_for(
            start_index + i,
            ranges,
            size,
        )

        x += draw.textlength(
            char,
            font=font,
        )

        i += 1

    return x


# ============================================================================
# WRAPPING
# ============================================================================

def _wrap_text(
    draw,
    text,
    max_width,
    ranges,
    size,
):
    """
    Wrap text without losing its original character indexes.
    """

    result = []

    current = ""
    current_start = 0

    cursor = 0

    for word in text.split(" "):

        if not current:
            candidate = word
            candidate_start = cursor
        else:
            candidate = (
                current
                + " "
                + word
            )
            candidate_start = current_start

        width = _measure(
            draw,
            candidate,
            candidate_start,
            ranges,
            size,
        )

        if current and width > max_width:

            result.append(
                (
                    current,
                    current_start,
                )
            )

            current = word
            current_start = cursor

        else:
            current = candidate

        cursor += len(word) + 1

    if current:
        result.append(
            (
                current,
                current_start,
            )
        )

    return result or [
        ("…", 0)
    ]


# ============================================================================
# DRAW FORMATTED TEXT
# ============================================================================

def _draw_formatted(
    draw,
    x,
    y,
    text,
    start_index,
    ranges,
    size,
):
    emoji_ranges = _emoji_ranges(text)
    efont = _emoji_font(size)

    i = 0

    while i < len(text):

        # ----------------------------------------------------------
        # Emoji
        # ----------------------------------------------------------

        found = _emoji_at(
            i,
            emoji_ranges,
        )

        if found and efont:

            end, value = found

            try:

                draw.text(
                    (x, y - 3),
                    value,
                    font=efont,
                    embedded_color=True,
                )

                bbox = draw.textbbox(
                    (x, y - 3),
                    value,
                    font=efont,
                )

                width = bbox[2] - bbox[0]

                x += max(
                    width,
                    size,
                )

                i = end
                continue

            except Exception:
                pass

        # ----------------------------------------------------------
        # Regular / Bold / Italic
        # ----------------------------------------------------------

        char = text[i]

        font = _font_for(
            start_index + i,
            ranges,
            size,
        )

        draw.text(
            (x, y),
            char,
            font=font,
            fill=TEXT_COLOR,
        )

        x += draw.textlength(
            char,
            font=font,
        )

        i += 1


# ============================================================================
# RENDER
# ============================================================================

def render_quote(
    avatar_img,
    name,
    message,
    user_id,
    entity_ranges=None,
):
    entity_ranges = (
        entity_ranges
        or []
    )

    accent = _accent_for(
        user_id
    )

    name_font = _font(
        FONT_BOLD,
        NAME_SIZE,
    )

    regular_font = _font(
        FONT_REG,
        TEXT_SIZE,
    )

    temp = Image.new(
        "RGBA",
        (10, 10),
    )

    measure_draw = ImageDraw.Draw(
        temp
    )

    bubble_width = (
        BUBBLE_RIGHT
        - BUBBLE_X
    )

    text_width = (
        bubble_width
        - (BUBBLE_PAD_X * 2)
    )

    lines = _wrap_text(
        measure_draw,
        message.strip() or "…",
        text_width,
        entity_ranges,
        TEXT_SIZE,
    )

    name_bbox = measure_draw.textbbox(
        (0, 0),
        name[:32],
        font=name_font,
    )

    name_height = (
        name_bbox[3]
        - name_bbox[1]
    )

    line_bbox = measure_draw.textbbox(
        (0, 0),
        "Ag",
        font=regular_font,
    )

    line_height = (
        line_bbox[3]
        - line_bbox[1]
        + LINE_SPACING
    )

    message_height = (
        len(lines)
        * line_height
    )

    bubble_height = (
        BUBBLE_PAD_TOP
        + name_height
        + 4
        + message_height
        + BUBBLE_PAD_BOTTOM
    )

    bubble_height = max(
        bubble_height,
        AVATAR_SIZE,
    )

    canvas_height = max(
        bubble_height + 40,
        AVATAR_SIZE + 48,
    )

    # Transparent canvas.
    canvas = Image.new(
        "RGBA",
        (
            W,
            canvas_height,
        ),
        (0, 0, 0, 0),
    )

    draw = ImageDraw.Draw(
        canvas
    )

    # ----------------------------------------------------------
    # Bubble
    # ----------------------------------------------------------

    draw.rounded_rectangle(
        (
            BUBBLE_X,
            BUBBLE_TOP,
            BUBBLE_RIGHT,
            BUBBLE_TOP + bubble_height,
        ),
        radius=BUBBLE_RADIUS,
        fill=BUBBLE,
    )

    # ----------------------------------------------------------
    # Avatar OUTSIDE bubble
    # ----------------------------------------------------------

    avatar = _circle_avatar(
        avatar_img,
        AVATAR_SIZE,
    )

    avatar_y = (
        BUBBLE_TOP
        + max(
            0,
            (bubble_height - AVATAR_SIZE)
            // 2,
        )
    )

    canvas.paste(
        avatar,
        (
            AVATAR_X,
            avatar_y,
        ),
        avatar,
    )

    # ----------------------------------------------------------
    # Username
    # ----------------------------------------------------------

    text_x = (
        BUBBLE_X
        + BUBBLE_PAD_X
    )

    name_y = (
        BUBBLE_TOP
        + BUBBLE_PAD_TOP
    )

    draw.text(
        (
            text_x,
            name_y,
        ),
        name[:32],
        font=name_font,
        fill=accent + (255,),
    )

    # ----------------------------------------------------------
    # Message
    # ----------------------------------------------------------

    text_y = (
        name_y
        + name_height
        + 4
    )

    for line, original_index in lines:

        _draw_formatted(
            draw,
            text_x,
            text_y,
            line,
            original_index,
            entity_ranges,
            TEXT_SIZE,
        )

        text_y += line_height

    # ----------------------------------------------------------
    # Telegram sticker dimensions
    # ----------------------------------------------------------

    width, height = canvas.size

    scale = min(
        512 / width,
        512 / height,
        1,
    )

    if scale < 1:

        canvas = canvas.resize(
            (
                max(
                    1,
                    round(width * scale),
                ),
                max(
                    1,
                    round(height * scale),
                ),
            ),
            Image.LANCZOS,
        )

    # ----------------------------------------------------------
    # WEBP
    # ----------------------------------------------------------

    buffer = io.BytesIO()

    canvas.save(
        buffer,
        format="WEBP",
        quality=95,
        method=6,
    )

    return buffer.getvalue()


# ============================================================================
# /Q COMMAND
# ============================================================================

@Client.on_message(
    filters.command("q")
)
async def quote_cmd(
    client,
    message,
):
    target = message.reply_to_message

    if not target or not (
        target.text
        or target.caption
    ):
        await message.reply_text(
            "Reply to a text message with `/q` "
            "to turn it into a quote sticker."
        )
        return

    user = target.from_user

    if user is None:
        await message.reply_text(
            "Can't quote that one — no sender info "
            "(anonymous admin or channel post)."
        )
        return

    status = await message.reply_text(
        "Framing that up... 🔥"
    )

    # ----------------------------------------------------------
    # Avatar
    # ----------------------------------------------------------

    avatar_img = None

    try:

        full_user = await client.get_users(
            user.id
        )

        if full_user and full_user.photo:

            with tempfile.TemporaryDirectory() as tmp:

                path = await client.download_media(
                    full_user.photo.big_file_id,
                    file_name=os.path.join(
                        tmp,
                        "avatar",
                    ),
                )

                if path:

                    avatar_img = (
                        Image.open(path)
                        .convert("RGBA")
                    )

                    avatar_img.load()

    except Exception:
        avatar_img = None

    if avatar_img is None:
        avatar_img = _fallback_avatar(
            user
        )

    # ----------------------------------------------------------
    # Text
    # ----------------------------------------------------------

    text = (
        target.text
        or target.caption
        or ""
    )

    text = text[:MAX_QUOTE_CHARS]

    name = (
        user.first_name
        or user.username
        or "Someone"
    )

    # ----------------------------------------------------------
    # Telegram entities
    # ----------------------------------------------------------

    entity_ranges = _entity_ranges(
        target
    )

    # ----------------------------------------------------------
    # Render
    # ----------------------------------------------------------

    try:

        data = await asyncio.to_thread(
            render_quote,
            avatar_img,
            name,
            text,
            user.id,
            entity_ranges,
        )

    except Exception as exc:

        await status.edit_text(
            "Couldn't render that one.\n"
            f"`{exc}`"
        )

        return

    # ----------------------------------------------------------
    # Send sticker
    # ----------------------------------------------------------

    webp_path = None

    try:

        with tempfile.NamedTemporaryFile(
            suffix=".webp",
            delete=False,
        ) as file:

            file.write(data)
            webp_path = file.name

        await client.send_sticker(
            message.chat.id,
            webp_path,
            emoji="💬",
            reply_to_message_id=target.id,
        )

        await status.delete()

    except RPCError as exc:

        await status.edit_text(
            f"Couldn't send that. (`{exc}`)"
        )

    finally:

        if (
            webp_path
            and os.path.exists(webp_path)
        ):
            try:
                os.unlink(webp_path)
            except OSError:
                pass
