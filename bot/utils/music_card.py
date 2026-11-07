import os
import io
import uuid
import requests
from PIL import Image, ImageDraw, ImageFont, ImageFilter

def load_font(size: int, bold: bool = True):
    paths = [
        "C:/Windows/Fonts/segoeuib.ttf" if bold else "C:/Windows/Fonts/segoeui.ttf",
        "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/calibrib.ttf" if bold else "C:/Windows/Fonts/calibri.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "arialbd.ttf" if bold else "arial.ttf"
    ]
    for p in paths:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                continue
    return ImageFont.load_default()

def create_smooth_mask(size, radius: int):
    scale = 4
    w, h = size[0] * scale, size[1] * scale
    mask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, w, h], radius=radius * scale, fill=255)
    return mask.resize(size, Image.Resampling.LANCZOS)

def create_music_player_card(
    title: str,
    artist: str,
    duration: str,
    requester: str,
    thumbnail_url: str = None,
    status: str = "NOW PLAYING",
    volume: int = 50,
    loop_mode: str = "OFF"
) -> str:
    card_w, card_h = 1050, 340
    
    card = Image.new("RGBA", (card_w, card_h), (11, 12, 17, 255))
    glow = Image.new("RGBA", (card_w, card_h), (0, 0, 0, 0))
    gdraw = ImageDraw.Draw(glow)
    gdraw.ellipse([card_w - 300, -120, card_w + 100, 240], fill=(244, 63, 94, 50))
    glow = glow.filter(ImageFilter.GaussianBlur(radius=65))
    card = Image.alpha_composite(card, glow)

    draw = ImageDraw.Draw(card)
    draw.rounded_rectangle(
        [10, 10, card_w - 10, card_h - 10],
        radius=28,
        fill=(16, 18, 25, 215),
        outline=(244, 63, 94, 140),
        width=2
    )

    f_status = load_font(14, bold=True)
    f_title = load_font(32, bold=True)
    f_artist = load_font(20, bold=False)
    f_req = load_font(15, bold=True)
    f_pill = load_font(14, bold=True)

    thumb_size = 236
    thumb_x, thumb_y = 42, 52
    thumb_img = None

    if thumbnail_url:
        try:
            r = requests.get(str(thumbnail_url), headers={'User-Agent': 'Mozilla/5.0'}, timeout=5)
            if r.status_code == 200:
                thumb_img = Image.open(io.BytesIO(r.content)).convert("RGBA").resize((thumb_size, thumb_size), Image.Resampling.LANCZOS)
        except Exception:
            thumb_img = None

    if not thumb_img:
        thumb_img = Image.new("RGBA", (thumb_size, thumb_size), (35, 38, 50, 255))

    thumb_mask = create_smooth_mask((thumb_size, thumb_size), 20)
    card.paste(thumb_img, (thumb_x, thumb_y), thumb_mask)

    text_x = 310
    
    draw.rounded_rectangle([text_x, 42, text_x + 155, 74], radius=10, fill=(244, 63, 94, 230))
    draw.text((text_x + 16, 49), str(status).upper(), fill=(255, 255, 255), font=f_status)

    draw.rounded_rectangle([text_x + 167, 42, text_x + 290, 74], radius=10, fill=(30, 35, 48, 230), outline=(255, 255, 255, 20), width=1)
    draw.text((text_x + 180, 49), f"VOL: {volume}%", fill=(200, 210, 225), font=f_pill)

    draw.rounded_rectangle([text_x + 302, 42, text_x + 435, 74], radius=10, fill=(30, 35, 48, 230), outline=(255, 255, 255, 20), width=1)
    draw.text((text_x + 315, 49), f"LOOP: {loop_mode}", fill=(200, 210, 225), font=f_pill)

    clean_title = str(title)[:34]
    clean_artist = str(artist)[:42]
    draw.text((text_x, 92), clean_title, fill=(255, 255, 255), font=f_title)
    draw.text((text_x, 138), f"By {clean_artist}", fill=(160, 170, 185), font=f_artist)
    draw.text((text_x, 178), f"REQUESTED BY: {str(requester).upper()}", fill=(115, 125, 142), font=f_req)

    bar_x = text_x
    bar_y = 222
    bar_w = card_w - bar_x - 45
    bar_h = 36

    track_img = Image.new("RGBA", (bar_w, bar_h), (23, 25, 34, 255))
    track_mask = create_smooth_mask((bar_w, bar_h), bar_h // 2)
    card.paste(track_img, (bar_x, bar_y), track_mask)
    draw.rounded_rectangle(
        [bar_x, bar_y, bar_x + bar_w, bar_y + bar_h],
        radius=bar_h // 2,
        outline=(255, 255, 255, 20),
        width=1
    )

    fill_w = max(int(bar_w * 0.45), bar_h)
    fill_grad = Image.new("RGBA", (fill_w, bar_h))
    fdraw = ImageDraw.Draw(fill_grad)
    for x in range(fill_w):
        r = int(244 + (219 - 244) * (x / max(fill_w, 1)))
        g = int(63 + (39 - 63) * (x / max(fill_w, 1)))
        b = int(94 + (119 - 94) * (x / max(fill_w, 1)))
        fdraw.line([(x, 0), (x, bar_h)], fill=(r, g, b, 255))
    fill_mask = create_smooth_mask((fill_w, bar_h), bar_h // 2)
    card.paste(fill_grad, (bar_x, bar_y), fill_mask)

    dur_str = f"DURATION: {duration}"
    f_dur = load_font(16, bold=True)
    db = draw.textbbox((0, 0), dur_str, font=f_dur)
    draw.text((bar_x + bar_w - (db[2] - db[0]) - 20, bar_y + 8), dur_str, fill=(255, 255, 255), font=f_dur)

    os.makedirs("bot/data", exist_ok=True)
    out_path = f"bot/data/music_{uuid.uuid4().hex[:8]}.png"
    card.convert("RGB").save(out_path, quality=95)
    return out_path