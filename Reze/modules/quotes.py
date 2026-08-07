"""
/quote (reply to any text message) renders a Quotly-style card - circular
avatar, name, wrapped message bubble - and sends it as a sticker. The
render pipeline here was prototyped and visually verified before being
wired into a command (avatar circle mask, bubble, text wrap all confirmed
working against Telegram's 512px static sticker spec).

Sent quote cards aren't auto-saved to the user's pack (most people don't
want every quote they make cluttering their permanent collection) - but
since it's sent as a real sticker, replying to it with /kang grabs it in,
same as any other sticker.
"""
import os
import io
import tempfile
import asyncio

from PIL import Image, ImageDraw, ImageFont
from pyrogram import Client, filters
from pyrogram.errors import RPCError

FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_REG = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
MAX_QUOTE_CHARS = 320

ACCENTS = [
    (120, 90, 200), (90, 160, 200), (200, 110, 90),
    (90, 180, 130), (200, 150, 60), (170, 90, 200),
]


def _accent_for(user_id: int):
    return ACCENTS[user_id % len(ACCENTS)]


def _fallback_avatar(user) -> Image.Image:
    size = 200
    color = _accent_for(user.id)
    img = Image.new("RGBA", (size, size), color + (255,))
    d = ImageDraw.Draw(img)
    initial = (user.first_name or user.username or "?")[0].upper()
    font = ImageFont.truetype(FONT_BOLD, 96)
    bbox = d.textbbox((0, 0), initial, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    d.text(((size - tw) / 2 - bbox[0], (size - th) / 2 - bbox[1]), initial, font=font, fill=(255, 255, 255, 255))
    return img


def _circle_avatar(img: Image.Image, size: int) -> Image.Image:
    img = img.convert("RGBA").resize((size, size), Image.LANCZOS)
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, size, size), fill=255)
    out = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    out.paste(img, (0, 0), mask)
    return out


def _wrap_text(draw, text, font, max_width):
    lines, cur = [], ""
    for word in text.split():
        test = (cur + " " + word).strip()
        if draw.textlength(test, font=font) <= max_width:
            cur = test
        else:
            if cur:
                lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def render_quote(avatar_img: Image.Image, name: str, message: str, user_id: int) -> bytes:
    accent = _accent_for(user_id)
    W = 512
    pad = 28
    avatar_size = 72
    name_font = ImageFont.truetype(FONT_BOLD, 28)
    msg_font = ImageFont.truetype(FONT_REG, 30)

    tmp = Image.new("RGBA", (10, 10))
    d = ImageDraw.Draw(tmp)
    text_area_w = W - pad * 3 - avatar_size
    lines = _wrap_text(d, message.strip() or "…", msg_font, text_area_w)
    line_h = msg_font.getbbox("Ag")[3] + 10
    content_h = max(avatar_size, 40 + len(lines) * line_h) + pad * 2
    H = min(content_h, 900)

    canvas = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)
    draw.rounded_rectangle([0, 0, W - 1, H - 1], radius=34, fill=(24, 24, 32, 235))

    av = _circle_avatar(avatar_img, avatar_size)
    canvas.paste(av, (pad, pad), av)
    draw.ellipse([pad, pad, pad + avatar_size, pad + avatar_size], outline=accent, width=3)

    tx = pad * 2 + avatar_size
    draw.text((tx, pad - 4), name[:28], font=name_font, fill=accent)
    ty = pad + 38
    for line in lines:
        if ty > H - pad - line_h:
            draw.text((tx, ty), "…", font=msg_font, fill=(235, 235, 240, 255))
            break
        draw.text((tx, ty), line, font=msg_font, fill=(235, 235, 240, 255))
        ty += line_h

    if canvas.width >= canvas.height:
        nw, nh = 512, max(1, round(canvas.height * 512 / canvas.width))
    else:
        nh, nw = 512, max(1, round(canvas.width * 512 / canvas.height))
    canvas = canvas.resize((nw, nh), Image.LANCZOS)
    buf = io.BytesIO()
    canvas.save(buf, format="WEBP", quality=95, method=6)
    return buf.getvalue()


@Client.on_message(filters.command("quote"))
async def quote_cmd(client, message):
    target = message.reply_to_message
    if not target or not (target.text or target.caption):
        await message.reply_text("Reply to a text message with `/quote` to turn it into a quote sticker.")
        return
    user = target.from_user
    if user is None:
        await message.reply_text("Can't quote that one — no sender info (anonymous admin or channel post).")
        return

    status = await message.reply_text("Framing that up... 🔥")

    avatar_img = None
    if user.photo:
        try:
            with tempfile.TemporaryDirectory() as tmp:
                path = await client.download_media(user.photo.small_file_id, file_name=os.path.join(tmp, "avatar"))
                if path:
                    loaded = Image.open(path).convert("RGBA")
                    loaded.load()
                    avatar_img = loaded
        except Exception:
            avatar_img = None
    if avatar_img is None:
        avatar_img = _fallback_avatar(user)

    text = (target.text or target.caption or "")[:MAX_QUOTE_CHARS]
    name = user.first_name or user.username or "Someone"

    try:
        data = await asyncio.to_thread(render_quote, avatar_img, name, text, user.id)
    except Exception:
        await status.edit_text("Couldn't render that one. Try again?")
        return

    with tempfile.NamedTemporaryFile(suffix=".webp", delete=False) as f:
        f.write(data)
        webp_path = f.name
    try:
        await client.send_sticker(message.chat.id, webp_path, reply_to_message_id=target.id)
        await status.delete()
    except RPCError as e:
        await status.edit_text(f"Couldn't send that. (`{e}`)")
    finally:
        os.unlink(webp_path)
