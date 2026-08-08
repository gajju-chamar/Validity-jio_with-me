"""
/q - Create a Telegram-style quote sticker from a replied message.

Layout:

    [avatar]   ┌──────────────────────────────┐
               │ Username                     │
               │ Message with emoji/text      │
               └──────────────────────────────┘

The avatar is completely outside the message bubble.

Design:
- Overall background: RGB(25, 20, 41)
- Dark Telegram-style message bubble
- User-specific username colour
- Avatar outside the bubble
- Emoji rendered using Noto Color Emoji
- Bold / italic Telegram entities preserved where possible
- Unicode mathematical/stylized characters supported through Noto fonts
"""

import asyncio
import io
import os
import tempfile

import emoji

from PIL import Image, ImageDraw, ImageFont

from pyrogram import Client, filters
from pyrogram.errors import RPCError
from pyrogram.enums import MessageEntityType


# ============================================================================
# FONTS
# ============================================================================

FONT_REGULAR_CANDIDATES = [
    "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf",
    "/usr/share/fonts/opentype/noto/NotoSans-Regular.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
]

FONT_BOLD_CANDIDATES = [
    "/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf",
    "/usr/share/fonts/opentype/noto/NotoSans-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
]

FONT_ITALIC_CANDIDATES = [
    "/usr/share/fonts/truetype/noto/NotoSans-Italic.ttf",
    "/usr/share/fonts/opentype/noto/NotoSans-Italic.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Oblique.ttf",
]

FONT_BOLD_ITALIC_CANDIDATES = [
    "/usr/share/fonts/truetype/noto/NotoSans-BoldItalic.ttf",
    "/usr/share/fonts/opentype/noto/NotoSans-BoldItalic.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-BoldOblique.ttf",
]

FONT_MATH_CANDIDATES = [
    "/usr/share/fonts/truetype/noto/NotoSansMath-Regular.ttf",
    "/usr/share/fonts/opentype/noto/NotoSansMath-Regular.ttf",
]

FONT_EMOJI_CANDIDATES = [
    "/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf",
]


def _find_font(candidates):
    for path in candidates:
        if os.path.exists(path):
            return path
    return None


FONT_REGULAR = _find_font(FONT_REGULAR_CANDIDATES)
FONT_BOLD = _find_font(FONT_BOLD_CANDIDATES)
FONT_ITALIC = _find_font(FONT_ITALIC_CANDIDATES)
FONT_BOLD_ITALIC = _find_font(FONT_BOLD_ITALIC_CANDIDATES)
FONT_MATH = _find_font(FONT_MATH_CANDIDATES)
FONT_EMOJI = _find_font(FONT_EMOJI_CANDIDATES)


def _load_font(path, size):
    if not path:
        raise RuntimeError(
            "Required quote font is missing from the Docker image."
        )

    return ImageFont.truetype(path, size)


# ============================================================================
# DESIGN
# ============================================================================

BACKGROUND = (25, 20, 41, 255)

# Telegram-ish dark bubble.
BUBBLE_BACKGROUND = (38, 32, 58, 255)

TEXT_COLOR = (242, 240, 246, 255)

MAX_QUOTE_CHARS = 320

CANVAS_WIDTH = 512

# Avatar sits outside the bubble.
AVATAR_SIZE = 68
AVATAR_X = 18
AVATAR_Y = 24

# Message bubble.
BUBBLE_X = 78
BUBBLE_RIGHT = 494
BUBBLE_Y = 20

BUBBLE_RADIUS = 17

BUBBLE_PADDING_X = 16
BUBBLE_PADDING_TOP = 12
BUBBLE_PADDING_BOTTOM = 14

NAME_SIZE = 22
MESSAGE_SIZE = 26

NAME_MESSAGE_GAP = 4
LINE_SPACING = 5


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

    image = Image.new(
        "RGBA",
        (size, size),
        accent + (255,),
    )

    draw = ImageDraw.Draw(image)

    initial_source = (
        user.first_name
        or user.username
        or "?"
    )

    initial = initial_source[0].upper()

    font = _load_font(
        FONT_BOLD,
        96,
    )

    bbox = draw.textbbox(
        (0, 0),
        initial,
        font=font,
    )

    width = bbox[2] - bbox[0]
    height = bbox[3] - bbox[1]

    draw.text(
        (
            (size - width) / 2 - bbox[0],
            (size - height) / 2 - bbox[1],
        ),
        initial,
        font=font,
        fill=(255, 255, 255, 255),
    )

    return image


def _circle_avatar(image, size):
    image = image.convert("RGBA")

    width, height = image.size

    if width != height:
        side = min(width, height)

        left = (width - side) // 2
        top = (height - side) // 2

        image = image.crop(
            (
                left,
                top,
                left + side,
                top + side,
            )
        )

    image = image.resize(
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

    output = Image.new(
        "RGBA",
        (size, size),
        (0, 0, 0, 0),
    )

    output.paste(
        image,
        (0, 0),
        mask,
    )

    return output


# ============================================================================
# FONT SELECTION
# ============================================================================

def _font_for_style(size, bold=False, italic=False):
    if bold and italic:
        path = FONT_BOLD_ITALIC or FONT_BOLD or FONT_REGULAR

    elif bold:
        path = FONT_BOLD or FONT_REGULAR

    elif italic:
        path = FONT_ITALIC or FONT_REGULAR

    else:
        path = FONT_REGULAR

    return _load_font(path, size)


def _looks_like_math_unicode(char):
    code = ord(char)

    return (
        0x1D400 <= code <= 0x1D7FF
        or 0x2100 <= code <= 0x214F
        or 0x2200 <= code <= 22FF
    )


def _font_for_character(
    char,
    size,
    bold=False,
    italic=False,
):
    """
    Use Noto Sans Math for mathematical/stylized Unicode characters.
    Otherwise use the requested normal/bold/italic font.
    """

    if _looks_like_math_unicode(char) and FONT_MATH:
        try:
            return _load_font(
                FONT_MATH,
                size,
            )
        except Exception:
            pass

    return _font_for_style(
        size,
        bold=bold,
        italic=italic,
    )


# ============================================================================
# ENTITY HANDLING
# ============================================================================

def _entity_ranges(message):
    """
    Convert Telegram entities into character ranges.

    Pyrogram exposes entity offsets/lengths in Telegram's UTF-16 based
    representation. Python strings use Unicode code points, so we map
    UTF-16 offsets back to Python indices.
    """

    text = message.text or message.caption or ""

    if not text:
        return []

    entities = (
        message.entities
        or message.caption_entities
        or []
    )

    result = []

    for entity in entities:

        entity_type = getattr(
            entity,
            "type",
            None,
        )

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

        if not length:
            continue

        utf16 = 0
        start = None
        end = None

        for index, char in enumerate(text):

            char_units = len(
                char.encode(
                    "utf-16-le"
                )
            ) // 2

            if utf16 == offset:
                start = index

            utf16 += char_units

            if utf16 == offset + length:
                end = index + 1
                break

        if start is None:
            start = 0

        if end is None:
            end = len(text)

        result.append(
            (
                start,
                end,
                str(entity_type).lower(),
            )
        )

    return result


def _style_for_position(
    index,
    entity_ranges,
):
    bold = False
    italic = False

    for start, end, entity_type in entity_ranges:

        if not (
            start <= index < end
        ):
            continue

        if "bold" in entity_type:
            bold = True

        if "italic" in entity_type:
            italic = True

    return bold, italic


# ============================================================================
# EMOJI HELPERS
# ============================================================================

def _emoji_spans(text):
    """
    Returns emoji spans so ZWJ emoji such as:
        👨‍💻
        ❤️
        👩🏽‍💻

    are treated as one visual unit instead of being split character by
    character.
    """

    spans = []

    try:
        for item in emoji.emoji_list(text):

            start = item["match_start"]
            end = item["match_end"]

            spans.append(
                (
                    start,
                    end,
                    item["emoji"],
                )
            )

    except Exception:
        pass

    return spans


# ============================================================================
# TEXT MEASUREMENT
# ============================================================================

def _segment_width(
    draw,
    text,
    size,
    bold=False,
    italic=False,
):
    if not text:
        return 0

    font = _font_for_style(
        size,
        bold=bold,
        italic=italic,
    )

    return draw.textlength(
        text,
        font=font,
    )


def _wrap_text(
    draw,
    text,
    max_width,
    size,
    entity_ranges,
):
    """
    Word wrapping that takes emoji and Telegram formatting into account.

    We keep words intact where possible.
    """

    words = text.split(" ")

    lines = []

    current = ""
    current_start = 0

    cursor = 0

    for word_index, word in enumerate(words):

        if word_index > 0:
            cursor += 1

        word_start = cursor
        word_end = word_start + len(word)

        candidate = (
            word
            if not current
            else f"{current} {word}"
        )

        # Approximate width using the actual style of the first
        # character in the candidate.
        test_width = 0

        for local_index, char in enumerate(candidate):

            absolute_index = (
                current_start
                + local_index
            )

            bold, italic = _style_for_position(
                absolute_index,
                entity_ranges,
            )

            emoji_spans = _emoji_spans(char)

            if emoji_spans and FONT_EMOJI:

                emoji_font = _load_font(
                    FONT_EMOJI,
                    size,
                )

                try:
                    bbox = draw.textbbox(
                        (0, 0),
                        char,
                        font=emoji_font,
                    )

                    width = bbox[2] - bbox[0]

                    if width <= 0:
                        width = size

                    test_width += width
                    continue

                except Exception:
                    pass

            font = _font_for_character(
                char,
                size,
                bold=bold,
                italic=italic,
            )

            test_width += draw.textlength(
                char,
                font=font,
            )

        if (
            current
            and test_width > max_width
        ):

            lines.append(
                (
                    current,
                    current_start,
                )
            )

            current = word
            current_start = word_start

        else:

            current = candidate

        cursor = word_end

    if current:
        lines.append(
            (
                current,
                current_start,
            )
        )

    return lines or [("…", 0)]


# ============================================================================
# MIXED TEXT RENDERING
# ============================================================================

def _draw_text_line(
    draw,
    x,
    y,
    text,
    absolute_start,
    size,
    color,
    entity_ranges,
):
    """
    Render a line character-by-character so normal text, bold, italic,
    Unicode mathematical characters and emoji can coexist.
    """

    emoji_spans = _emoji_spans(text)

    emoji_lookup = {}

    for start, end, value in emoji_spans:
        emoji_lookup[start] = (
            end,
            value,
        )

    index = 0

    while index < len(text):

        # --------------------------------------------------------------
        # Emoji
        # --------------------------------------------------------------

        if index in emoji_lookup and FONT_EMOJI:

            end, emoji_value = emoji_lookup[index]

            try:
                emoji_font = _load_font(
                    FONT_EMOJI,
                    size,
                )

                draw.text(
                    (
                        x,
                        y - 3,
                    ),
                    emoji_value,
                    font=emoji_font,
                    embedded_color=True,
                )

                bbox = draw.textbbox(
                    (
                        x,
                        y - 3,
                    ),
                    emoji_value,
                    font=emoji_font,
                )

                width = bbox[2] - bbox[0]

                if width <= 0:
                    width = size

                x += width

                index = end
                continue

            except Exception:
                pass

        # --------------------------------------------------------------
        # Normal / bold / italic / math character
        # --------------------------------------------------------------

        char = text[index]

        bold, italic = _style_for_position(
            absolute_start + index,
            entity_ranges,
        )

        font = _font_for_character(
            char,
            size,
            bold=bold,
            italic=italic,
        )

        draw.text(
            (
                x,
                y,
            ),
            char,
            font=font,
            fill=color,
        )

        x += draw.textlength(
            char,
            font=font,
        )

        index += 1


# ============================================================================
# QUOTE RENDERER
# ============================================================================

def render_quote(
    avatar_img,
    name,
    message,
    user_id,
    entity_ranges=None,
):
    accent = _accent_for(user_id)

    entity_ranges = entity_ranges or []

    name_font = _load_font(
        FONT_BOLD,
        NAME_SIZE,
    )

    message_font = _load_font(
        FONT_REGULAR,
        MESSAGE_SIZE,
    )

    temp = Image.new(
        "RGBA",
        (10, 10),
    )

    measure = ImageDraw.Draw(temp)

    # --------------------------------------------------------------
    # Bubble dimensions
    # --------------------------------------------------------------

    bubble_width = (
        BUBBLE_RIGHT
        - BUBBLE_X
    )

    text_width = (
        bubble_width
        - BUBBLE_PADDING_X * 2
    )

    wrapped_lines = _wrap_text(
        measure,
        message.strip() or "…",
        text_width,
        MESSAGE_SIZE,
        entity_ranges,
    )

    name_bbox = measure.textbbox(
        (0, 0),
        name[:32],
        font=name_font,
    )

    name_height = (
        name_bbox[3]
        - name_bbox[1]
    )

    message_bbox = measure.textbbox(
        (0, 0),
        "Ag",
        font=message_font,
    )

    line_height = (
        message_bbox[3]
        - message_bbox[1]
        + LINE_SPACING
    )

    message_height = (
        len(wrapped_lines)
        * line_height
    )

    bubble_height = (
        BUBBLE_PADDING_TOP
        + name_height
        + NAME_MESSAGE_GAP
        + message_height
        + BUBBLE_PADDING_BOTTOM
    )

    bubble_height = max(
        bubble_height,
        AVATAR_SIZE,
    )

    # --------------------------------------------------------------
    # Canvas
    # --------------------------------------------------------------

    canvas_height = max(
        bubble_height + 40,
        AVATAR_SIZE + 48,
    )

    canvas = Image.new(
        "RGBA",
        (
            CANVAS_WIDTH,
            canvas_height,
        ),
        BACKGROUND,
    )

    draw = ImageDraw.Draw(canvas)

    # --------------------------------------------------------------
    # Message bubble
    # --------------------------------------------------------------

    draw.rounded_rectangle(
        (
            BUBBLE_X,
            BUBBLE_Y,
            BUBBLE_RIGHT,
            BUBBLE_Y + bubble_height,
        ),
        radius=BUBBLE_RADIUS,
        fill=BUBBLE_BACKGROUND,
    )

    # --------------------------------------------------------------
    # Avatar OUTSIDE bubble
    # --------------------------------------------------------------

    avatar = _circle_avatar(
        avatar_img,
        AVATAR_SIZE,
    )

    avatar_y = (
        BUBBLE_Y
        + max(
            0,
            (bubble_height - AVATAR_SIZE) // 2,
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

    # Very subtle user-coloured outline.
    draw.ellipse(
        (
            AVATAR_X,
            avatar_y,
            AVATAR_X + AVATAR_SIZE - 1,
            avatar_y + AVATAR_SIZE - 1,
        ),
        outline=accent + (210,),
        width=2,
    )

    # --------------------------------------------------------------
    # Username
    # --------------------------------------------------------------

    text_x = (
        BUBBLE_X
        + BUBBLE_PADDING_X
    )

    name_y = (
        BUBBLE_Y
        + BUBBLE_PADDING_TOP
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

    # --------------------------------------------------------------
    # Message
    # --------------------------------------------------------------

    message_y = (
        name_y
        + name_height
        + NAME_MESSAGE_GAP
    )

    for line, absolute_start in wrapped_lines:

        _draw_text_line(
            draw,
            text_x,
            message_y,
            line,
            absolute_start,
            MESSAGE_SIZE,
            TEXT_COLOR,
            entity_ranges,
        )

        message_y += line_height

    # --------------------------------------------------------------
    # Telegram sticker size
    # --------------------------------------------------------------

    width, height = canvas.size

    scale = min(
        512 / width,
        512 / height,
        1,
    )

    if scale != 1:

        canvas = canvas.resize(
            (
                max(1, round(width * scale)),
                max(1, round(height * scale)),
            ),
            Image.LANCZOS,
        )

    # --------------------------------------------------------------
    # WEBP
    # --------------------------------------------------------------

    buffer = io.BytesIO()

    canvas.save(
        buffer,
        format="WEBP",
        quality=95,
        method=6,
    )

    return buffer.getvalue()


# ============================================================================
# /q COMMAND
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

    # --------------------------------------------------------------
    # Fetch avatar
    # --------------------------------------------------------------

    avatar_img = None

    try:
        full_user = await client.get_users(
            user.id
        )

        if full_user and full_user.photo:

            with tempfile.TemporaryDirectory() as tmp:

                avatar_path = await client.download_media(
                    full_user.photo.big_file_id,
                    file_name=os.path.join(
                        tmp,
                        "avatar",
                    ),
                )

                if avatar_path:

                    avatar_img = (
                        Image.open(
                            avatar_path
                        )
                        .convert("RGBA")
                    )

                    avatar_img.load()

    except Exception:
        avatar_img = None

    if avatar_img is None:
        avatar_img = _fallback_avatar(user)

    # --------------------------------------------------------------
    # Text
    # --------------------------------------------------------------

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

    # --------------------------------------------------------------
    # Telegram formatting entities
    # --------------------------------------------------------------

    entity_ranges = _entity_ranges(
        target
    )

    # --------------------------------------------------------------
    # Render
    # --------------------------------------------------------------

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

    # --------------------------------------------------------------
    # Send sticker
    # --------------------------------------------------------------

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
