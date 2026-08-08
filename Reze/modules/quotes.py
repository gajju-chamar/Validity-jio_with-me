"""
/q - Create a Telegram-style quote sticker from a replied message.

Design:
- Dark Telegram-like message bubble
- User-specific accent colour for the name
- Avatar outside the message bubble
- Small "thinking" indicator beside the avatar
- Unicode-friendly fonts for stylized names
- Automatic text wrapping
- 512px Telegram sticker-compatible output

The generated sticker is not automatically saved to a user's sticker pack.
Replying to it with /kang can still save it like any other sticker.
"""

import asyncio
import io
import os
import tempfile

from PIL import Image, ImageDraw, ImageFont

from pyrogram import Client, filters
from pyrogram.errors import RPCError


# ---------------------------------------------------------------------------
# Fonts
# ---------------------------------------------------------------------------

# Noto Sans has much broader Unicode coverage than DejaVu Sans.
# This matters for names containing stylized Unicode characters such as:
#
# 𝑺𝒂𝒏𝒋𝒊
# 𝘚𝘢𝘯𝘫𝘪
# 𝗦𝗮𝗻𝗷𝗶
# 𝓢𝓪𝓷𝓳𝓲
#
# We keep DejaVu as a fallback for systems where Noto isn't installed.

FONT_CANDIDATES = {
    "regular": [
        "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf",
        "/usr/share/fonts/opentype/noto/NotoSans-Regular.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ],
    "bold": [
        "/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf",
        "/usr/share/fonts/opentype/noto/NotoSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ],
}


def _find_font(kind: str) -> str:
    """
    Find the first available font from our candidate list.
    """

    for path in FONT_CANDIDATES[kind]:
        if os.path.exists(path):
            return path

    raise FileNotFoundError(
        f"No usable {kind} font found. "
        f"Checked: {FONT_CANDIDATES[kind]}"
    )


FONT_REG = _find_font("regular")
FONT_BOLD = _find_font("bold")


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MAX_QUOTE_CHARS = 320

CANVAS_W = 512

# Overall margins
LEFT_MARGIN = 20
RIGHT_MARGIN = 20
TOP_MARGIN = 22
BOTTOM_MARGIN = 22

# Avatar
AVATAR_SIZE = 68

# Gap between avatar and bubble
AVATAR_GAP = 12

# Bubble
BUBBLE_RADIUS = 22
BUBBLE_PADDING_X = 18
BUBBLE_PADDING_TOP = 12
BUBBLE_PADDING_BOTTOM = 15

# Text
NAME_SIZE = 24
MESSAGE_SIZE = 27

NAME_TO_MESSAGE_GAP = 4
LINE_SPACING = 7


# ---------------------------------------------------------------------------
# User colours
# ---------------------------------------------------------------------------

# Each Telegram user gets a stable accent colour.
#
# This is intentionally NOT the bot's colour.
# user_id -> same colour every time.

ACCENTS = [
    (95, 155, 225),    # blue
    (210, 115, 105),   # coral
    (120, 180, 135),   # green
    (205, 155, 70),    # gold
    (175, 110, 205),   # purple
    (90, 180, 190),    # cyan
    (220, 125, 160),   # pink
]


def _accent_for(user_id: int):
    return ACCENTS[user_id % len(ACCENTS)]


# ---------------------------------------------------------------------------
# Font helpers
# ---------------------------------------------------------------------------

def _load_font(path: str, size: int):
    return ImageFont.truetype(path, size)


def _font_regular(size: int):
    return _load_font(FONT_REG, size)


def _font_bold(size: int):
    return _load_font(FONT_BOLD, size)


# ---------------------------------------------------------------------------
# Avatar
# ---------------------------------------------------------------------------

def _fallback_avatar(user) -> Image.Image:
    """
    Generate a simple avatar when Telegram doesn't provide a profile photo.
    """

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

    font = _font_bold(96)

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

    return img


def _circle_avatar(
    img: Image.Image,
    size: int,
) -> Image.Image:
    """
    Convert any avatar into a circular transparent image.
    """

    img = img.convert("RGBA")

    # Center-crop instead of stretching the avatar.
    width, height = img.size

    if width != height:
        side = min(width, height)

        left = (width - side) // 2
        top = (height - side) // 2

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

    output = Image.new(
        "RGBA",
        (size, size),
        (0, 0, 0, 0),
    )

    output.paste(
        img,
        (0, 0),
        mask,
    )

    return output


# ---------------------------------------------------------------------------
# Thinking indicator
# ---------------------------------------------------------------------------

def _draw_thinking_indicator(
    canvas: Image.Image,
    x: int,
    y: int,
):
    """
    Draw a tiny three-dot thought bubble next to the avatar.

    Since this is a static sticker, it cannot actually animate.
    The dots visually imply that the quoted person is "thinking".
    """

    draw = ImageDraw.Draw(canvas)

    # Small thought trail
    draw.ellipse(
        [
            x + 1,
            y + 28,
            x + 8,
            y + 35,
        ],
        fill=(75, 82, 100, 255),
    )

    draw.ellipse(
        [
            x + 7,
            y + 20,
            x + 17,
            y + 30,
        ],
        fill=(75, 82, 100, 255),
    )

    # Main bubble
    bubble_x = x + 13
    bubble_y = y

    bubble_w = 50
    bubble_h = 31

    draw.rounded_rectangle(
        [
            bubble_x,
            bubble_y,
            bubble_x + bubble_w,
            bubble_y + bubble_h,
        ],
        radius=15,
        fill=(35, 40, 52, 245),
        outline=(75, 82, 100, 255),
        width=1,
    )

    # Three dots
    dot_y = bubble_y + bubble_h // 2

    for index in range(3):
        dot_x = bubble_x + 14 + index * 11

        draw.ellipse(
            [
                dot_x - 3,
                dot_y - 3,
                dot_x + 3,
                dot_y + 3,
            ],
            fill=(155, 160, 180, 255),
        )


# ---------------------------------------------------------------------------
# Text wrapping
# ---------------------------------------------------------------------------

def _wrap_text(
    draw,
    text: str,
    font,
    max_width: int,
):
    """
    Wrap text while respecting words.

    Also handles very long individual words by splitting them.
    """

    lines = []

    for paragraph in text.split("\n"):
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

            if draw.textlength(
                candidate,
                font=font,
            ) <= max_width:

                current = candidate
                continue

            # Current line is full.
            if current:
                lines.append(current)

            # Word itself is wider than the available space.
            if draw.textlength(
                word,
                font=font,
            ) > max_width:

                chunk = ""

                for char in word:
                    test = chunk + char

                    if draw.textlength(
                        test,
                        font=font,
                    ) <= max_width:
                        chunk = test
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


# ---------------------------------------------------------------------------
# Render quote
# ---------------------------------------------------------------------------

def render_quote(
    avatar_img: Image.Image,
    name: str,
    message: str,
    user_id: int,
) -> bytes:

    accent = _accent_for(user_id)

    name_font = _font_bold(NAME_SIZE)
    message_font = _font_regular(MESSAGE_SIZE)

    # Temporary drawing surface used for measuring text.
    measure = Image.new(
        "RGBA",
        (10, 10),
    )

    measure_draw = ImageDraw.Draw(measure)

    # The bubble occupies the right side.
    bubble_x = (
        LEFT_MARGIN
        + AVATAR_SIZE
        + AVATAR_GAP
    )

    bubble_max_width = (
        CANVAS_W
        - bubble_x
        - RIGHT_MARGIN
    )

    text_width = (
        bubble_max_width
        - BUBBLE_PADDING_X * 2
    )

    # Wrap message.
    lines = _wrap_text(
        measure_draw,
        message.strip() or "…",
        message_font,
        text_width,
    )

    # Name dimensions.
    name_bbox = measure_draw.textbbox(
        (0, 0),
        name[:32],
        font=name_font,
    )

    name_height = (
        name_bbox[3]
        - name_bbox[1]
    )

    # Message line height.
    msg_bbox = measure_draw.textbbox(
        (0, 0),
        "Ag",
        font=message_font,
    )

    message_line_height = (
        msg_bbox[3]
        - msg_bbox[1]
        + LINE_SPACING
    )

    message_height = (
        len(lines)
        * message_line_height
    )

    bubble_height = (
        BUBBLE_PADDING_TOP
        + name_height
        + NAME_TO_MESSAGE_GAP
        + message_height
        + BUBBLE_PADDING_BOTTOM
    )

    # Minimum height so very short quotes still look good.
    bubble_height = max(
        bubble_height,
        AVATAR_SIZE,
    )

    # Maximum sticker height.
    bubble_height = min(
        bubble_height,
        760,
    )

    canvas_h = max(
        bubble_height + TOP_MARGIN + BOTTOM_MARGIN,
        AVATAR_SIZE + TOP_MARGIN + BOTTOM_MARGIN,
    )

    canvas = Image.new(
        "RGBA",
        (
            CANVAS_W,
            canvas_h,
        ),
        (0, 0, 0, 0),
    )

    draw = ImageDraw.Draw(canvas)

    # ------------------------------------------------------------------
    # Bubble
    # ------------------------------------------------------------------

    bubble_y = TOP_MARGIN

    # This is deliberately neutral/dark.
    # The name provides the user's colour.
    bubble_color = (24, 29, 39, 255)

    draw.rounded_rectangle(
        [
            bubble_x,
            bubble_y,
            CANVAS_W - RIGHT_MARGIN,
            bubble_y + bubble_height,
        ],
        radius=BUBBLE_RADIUS,
        fill=bubble_color,
    )

    # Tiny Telegram-style bottom-left tail.
    tail_x = bubble_x + 1
    tail_y = bubble_y + bubble_height - 18

    draw.polygon(
        [
            (tail_x, tail_y),
            (tail_x - 10, tail_y + 14),
            (tail_x + 14, tail_y + 7),
        ],
        fill=bubble_color,
    )

    # ------------------------------------------------------------------
    # Avatar
    # ------------------------------------------------------------------

    avatar = _circle_avatar(
        avatar_img,
        AVATAR_SIZE,
    )

    avatar_x = LEFT_MARGIN
    avatar_y = TOP_MARGIN + 2

    canvas.paste(
        avatar,
        (
            avatar_x,
            avatar_y,
        ),
        avatar,
    )

    # User-specific avatar ring.
    draw.ellipse(
        [
            avatar_x,
            avatar_y,
            avatar_x + AVATAR_SIZE - 1,
            avatar_y + AVATAR_SIZE - 1,
        ],
        outline=accent,
        width=2,
    )

    # Thinking indicator.
    #
    # Positioned above/right of the avatar so it looks detached
    # from the actual message bubble.
    indicator_x = avatar_x + 30
    indicator_y = avatar_y - 4

    _draw_thinking_indicator(
        canvas,
        indicator_x,
        indicator_y,
    )

    # ------------------------------------------------------------------
    # Name
    # ------------------------------------------------------------------

    text_x = (
        bubble_x
        + BUBBLE_PADDING_X
    )

    name_y = (
        bubble_y
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

    # ------------------------------------------------------------------
    # Message
    # ------------------------------------------------------------------

    message_y = (
        name_y
        + name_height
        + NAME_TO_MESSAGE_GAP
    )

    for line in lines:

        draw.text(
            (
                text_x,
                message_y,
            ),
            line,
            font=message_font,
            fill=(235, 238, 244, 255),
        )

        message_y += message_line_height

    # ------------------------------------------------------------------
    # Telegram sticker size
    # ------------------------------------------------------------------

    width, height = canvas.size

    if width >= height:

        new_width = 512

        new_height = max(
            1,
            round(
                height
                * 512
                / width
            ),
        )

    else:

        new_height = 512

        new_width = max(
            1,
            round(
                width
                * 512
                / height
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
    # WEBP output
    # ------------------------------------------------------------------

    buffer = io.BytesIO()

    canvas.save(
        buffer,
        format="WEBP",
        quality=95,
        method=6,
    )

    return buffer.getvalue()


# ---------------------------------------------------------------------------
# /q command
# ---------------------------------------------------------------------------

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
    # Download avatar
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

                    loaded = Image.open(
                        avatar_path
                    ).convert("RGBA")

                    loaded.load()

                    avatar_img = loaded

    except Exception:
        avatar_img = None

    if avatar_img is None:
        avatar_img = _fallback_avatar(user)

    # ------------------------------------------------------------------
    # Message text
    # ------------------------------------------------------------------

    text = (
        target.text
        or target.caption
        or ""
    )

    text = text[:MAX_QUOTE_CHARS]

    # Use the actual display name.
    #
    # Telegram may provide Unicode-styled names such as:
    # 𝘚𝘢𝘯𝘫𝘪
    # 𝗦𝗮𝗻𝗷𝗶
    # 𝑺𝒂𝒏𝒋𝒊
    #
    # Noto Sans handles these much better than DejaVu Sans.

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
            "Couldn't render that one. "
            f"(`{exc}`)"
        )

        return

    # ------------------------------------------------------------------
    # Send sticker
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

        if webp_path and os.path.exists(
            webp_path
        ):
            try:
                os.unlink(webp_path)
            except OSError:
                pass
