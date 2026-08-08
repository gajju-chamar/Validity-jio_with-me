"""
/q - Create a Telegram-style quote sticker from a replied message.

Design:
- Background: RGB(25, 20, 41)
- Avatar outside the comment card
- User-specific name colour
- Comment-style card, not a speech bubble
- Unicode-friendly text rendering
- Color emoji support
- Preserves common Telegram text formatting where possible
"""

import asyncio
import io
import os
import tempfile

from PIL import Image, ImageDraw, ImageFont

from pyrogram import Client, filters
from pyrogram.errors import RPCError


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
FONT_EMOJI = _find_font(FONT_EMOJI_CANDIDATES)


def _load_font(path, size):
    if not path:
        raise RuntimeError("Required font is not installed.")
    return ImageFont.truetype(path, size)


# ============================================================================
# DESIGN
# ============================================================================

BACKGROUND = (25, 20, 41, 255)

# Dark comment-card colour.
CARD_BACKGROUND = (32, 27, 50, 255)

TEXT_COLOR = (240, 238, 245, 255)
SECONDARY_COLOR = (165, 160, 180, 255)

MAX_QUOTE_CHARS = 320

CANVAS_WIDTH = 512

AVATAR_SIZE = 72
AVATAR_X = 20
AVATAR_Y = 24

CARD_X = 106
CARD_Y = 24
CARD_RIGHT = 492

CARD_RADIUS = 20

CARD_PADDING_X = 18
CARD_PADDING_TOP = 14
CARD_PADDING_BOTTOM = 17

NAME_SIZE = 23
MESSAGE_SIZE = 27

LINE_SPACING = 7
NAME_MESSAGE_GAP = 5


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
# THINKING / COMMENT INDICATOR
# ============================================================================

def _draw_comment_indicator(
    canvas,
    avatar_x,
    avatar_y,
):
    """
    Small comment-style indicator attached visually to the avatar.
    """

    draw = ImageDraw.Draw(canvas)

    x = avatar_x + 45
    y = avatar_y + 48

    # Outer little comment bubble
    draw.rounded_rectangle(
        (
            x,
            y,
            x + 42,
            y + 27,
        ),
        radius=13,
        fill=(45, 39, 63, 255),
    )

    # Tiny tail
    draw.polygon(
        (
            (x + 8, y + 22),
            (x + 4, y + 31),
            (x + 16, y + 23),
        ),
        fill=(45, 39, 63, 255),
    )

    # Three dots
    for i in range(3):
        dot_x = x + 11 + i * 10

        draw.ellipse(
            (
                dot_x - 2,
                y + 11 - 2,
                dot_x + 2,
                y + 11 + 2,
            ),
            fill=(180, 174, 195, 255),
        )


# ============================================================================
# TEXT HELPERS
# ============================================================================

def _text_width(draw, text, font):
    return draw.textlength(
        text,
        font=font,
    )


def _wrap_text(
    draw,
    text,
    font,
    max_width,
):
    """
    Wrap text while keeping words intact where possible.
    """

    lines = []

    paragraphs = text.split("\n")

    for paragraph in paragraphs:

        paragraph = paragraph.strip()

        if not paragraph:
            lines.append("")
            continue

        current = ""

        for word in paragraph.split():

            candidate = (
                f"{current} {word}"
                if current
                else word
            )

            if _text_width(
                draw,
                candidate,
                font,
            ) <= max_width:

                current = candidate
                continue

            if current:
                lines.append(current)

            # Extremely long word.
            if _text_width(
                draw,
                word,
                font,
            ) > max_width:

                chunk = ""

                for char in word:

                    candidate_char = chunk + char

                    if _text_width(
                        draw,
                        candidate_char,
                        font,
                    ) <= max_width:

                        chunk = candidate_char

                    else:

                        if chunk:
                            lines.append(chunk)

                        chunk = char

                current = chunk

            else:
                current = word

        if current:
            lines.append(current)

    return lines or ["…"]


# ============================================================================
# EMOJI DETECTION
# ============================================================================

def _is_emoji_char(char):
    """
    Basic emoji range detection.

    This isn't intended to classify every Unicode character perfectly.
    It catches the emoji ranges most commonly used in Telegram messages.
    """

    code = ord(char)

    return (
        0x1F000 <= code <= 0x1FAFF
        or 0x2600 <= code <= 0x27BF
        or 0x2300 <= code <= 0x23FF
        or 0x2B00 <= code <= 0x2BFF
    )


def _contains_emoji(text):
    return any(
        _is_emoji_char(char)
        for char in text
    )


# ============================================================================
# MIXED TEXT RENDERER
# ============================================================================

def _draw_mixed_text(
    draw,
    position,
    text,
    regular_font,
    emoji_font,
    fill,
):
    """
    Draw normal Unicode text with Noto Sans and emoji using
    Noto Color Emoji.

    This prevents emoji from becoming empty squares.
    """

    x, y = position

    if not emoji_font:
        draw.text(
            (x, y),
            text,
            font=regular_font,
            fill=fill,
        )
        return

    current = ""

    def flush_text():
        nonlocal current, x

        if not current:
            return

        draw.text(
            (x, y),
            current,
            font=regular_font,
            fill=fill,
        )

        x += draw.textlength(
            current,
            font=regular_font,
        )

        current = ""

    for char in text:

        if _is_emoji_char(char):

            flush_text()

            try:
                draw.text(
                    (x, y - 2),
                    char,
                    font=emoji_font,
                    embedded_color=True,
                )

                bbox = draw.textbbox(
                    (x, y - 2),
                    char,
                    font=emoji_font,
                )

                emoji_width = bbox[2] - bbox[0]

                if emoji_width <= 0:
                    emoji_width = 30

                x += emoji_width

            except Exception:
                # If Pillow cannot render a specific emoji,
                # fall back gracefully rather than crashing.
                fallback = "□"

                draw.text(
                    (x, y),
                    fallback,
                    font=regular_font,
                    fill=fill,
                )

                x += draw.textlength(
                    fallback,
                    font=regular_font,
                )

        else:
            current += char

    flush_text()


# ============================================================================
# QUOTE RENDERER
# ============================================================================

def render_quote(
    avatar_img,
    name,
    message,
    user_id,
):
    accent = _accent_for(user_id)

    name_font = _load_font(
        FONT_BOLD,
        NAME_SIZE,
    )

    message_font = _load_font(
        FONT_REGULAR,
        MESSAGE_SIZE,
    )

    emoji_font = None

    if FONT_EMOJI:
        try:
            emoji_font = ImageFont.truetype(
                FONT_EMOJI,
                MESSAGE_SIZE,
            )
        except Exception:
            emoji_font = None

    # Temporary measurement surface.
    temp = Image.new(
        "RGBA",
        (10, 10),
    )

    measure = ImageDraw.Draw(temp)

    # Text area inside the comment card.
    text_width = (
        CARD_RIGHT
        - CARD_X
        - CARD_PADDING_X * 2
    )

    lines = _wrap_text(
        measure,
        message.strip() or "…",
        message_font,
        text_width,
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

    msg_bbox = measure.textbbox(
        (0, 0),
        "Ag",
        font=message_font,
    )

    line_height = (
        msg_bbox[3]
        - msg_bbox[1]
        + LINE_SPACING
    )

    message_height = (
        len(lines)
        * line_height
    )

    card_height = (
        CARD_PADDING_TOP
        + name_height
        + NAME_MESSAGE_GAP
        + message_height
        + CARD_PADDING_BOTTOM
    )

    card_height = max(
        card_height,
        AVATAR_SIZE,
    )

    card_height = min(
        card_height,
        760,
    )

    canvas_height = (
        max(
            card_height,
            AVATAR_SIZE,
        )
        + 48
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

    # ------------------------------------------------------------------
    # Avatar
    # ------------------------------------------------------------------

    avatar = _circle_avatar(
        avatar_img,
        AVATAR_SIZE,
    )

    canvas.paste(
        avatar,
        (
            AVATAR_X,
            AVATAR_Y,
        ),
        avatar,
    )

    # User's accent ring.
    draw.ellipse(
        (
            AVATAR_X,
            AVATAR_Y,
            AVATAR_X + AVATAR_SIZE - 1,
            AVATAR_Y + AVATAR_SIZE - 1,
        ),
        outline=accent + (255,),
        width=2,
    )

    # Comment/thinking indicator.
    _draw_comment_indicator(
        canvas,
        AVATAR_X,
        AVATAR_Y,
    )

    # ------------------------------------------------------------------
    # Comment card
    # ------------------------------------------------------------------

    draw.rounded_rectangle(
        (
            CARD_X,
            CARD_Y,
            CARD_RIGHT,
            CARD_Y + card_height,
        ),
        radius=CARD_RADIUS,
        fill=CARD_BACKGROUND,
    )

    # ------------------------------------------------------------------
    # Username
    # ------------------------------------------------------------------

    text_x = (
        CARD_X
        + CARD_PADDING_X
    )

    name_y = (
        CARD_Y
        + CARD_PADDING_TOP
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

    # ------------------------------------------------------------------
    # Message
    # ------------------------------------------------------------------

    message_y = (
        name_y
        + name_height
        + NAME_MESSAGE_GAP
    )

    for line in lines:

        _draw_mixed_text(
            draw,
            (
                text_x,
                message_y,
            ),
            line,
            message_font,
            emoji_font,
            TEXT_COLOR,
        )

        message_y += line_height

    # ------------------------------------------------------------------
    # Resize to Telegram sticker dimensions
    # ------------------------------------------------------------------

    width, height = canvas.size

    if width >= height:

        new_width = 512

        new_height = max(
            1,
            round(
                height
                * 512
                / width,
            ),
        )

    else:

        new_height = 512

        new_width = max(
            1,
            round(
                width
                * 512
                / height,
            ),
        )

    canvas = canvas.resize(
        (
            new_width,
            new_height,
        ),
        Image.LANCZOS,
    )

    # ------------------------------------------------------------------
    # WEBP
    # ------------------------------------------------------------------

    buffer = io.BytesIO()

    canvas.save(
        buffer,
        format="WEBP",
        quality=95,
        method=6,
    )

    return buffer.getvalue()


# ============================================================================
# /q
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

    # ------------------------------------------------------------------
    # Avatar
    # ------------------------------------------------------------------

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

    # ------------------------------------------------------------------
    # Message
    # ------------------------------------------------------------------

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

    # ------------------------------------------------------------------
    # Render
    # ------------------------------------------------------------------

    try:

        data = await asyncio.to_thread(
            render_quote,
            avatar_img,
            name,
            text,
            user.id,
        )

    except Exception as exc:

        await status.edit_text(
            "Couldn't render that one.\n"
            f"`{exc}`"
        )

        return

    # ------------------------------------------------------------------
    # Send
    # ------------------------------------------------------------------

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
