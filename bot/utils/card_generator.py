import os
import io
import uuid
import math
import requests
from PIL import Image, ImageDraw, ImageFont, ImageFilter

# ==============================================================================
# THEME PALETTES & COLOR CONFIGURATIONS
# ==============================================================================
THEMES = {
    "crimson": {
        "name": "Crimson Rose",
        "bar_start": (255, 65, 95),
        "bar_end": (190, 18, 60),
        "accent": (255, 95, 120),
        "glow": (244, 63, 94)
    },
    "neon_violet": {
        "name": "Cyber Violet",
        "bar_start": (192, 132, 252),
        "bar_end": (109, 40, 217),
        "accent": (216, 180, 254),
        "glow": (139, 92, 246)
    },
    "emerald": {
        "name": "Emerald Matrix",
        "bar_start": (52, 211, 153),
        "bar_end": (5, 150, 105),
        "accent": (110, 231, 183),
        "glow": (16, 185, 129)
    },
    "gold": {
        "name": "Royal Gold",
        "bar_start": (251, 191, 36),
        "bar_end": (180, 83, 9),
        "accent": (253, 224, 71),
        "glow": (245, 158, 11)
    },
    "ocean": {
        "name": "Electric Ocean",
        "bar_start": (56, 189, 248),
        "bar_end": (29, 78, 216),
        "accent": (125, 211, 252),
        "glow": (14, 165, 233)
    },
    "sunset": {
        "name": "Sunset Blaze",
        "bar_start": (251, 146, 60),
        "bar_end": (225, 29, 72),
        "accent": (253, 186, 116),
        "glow": (249, 115, 22)
    },
    "cyber_pink": {
        "name": "Tokyo Neon",
        "bar_start": (244, 114, 182),
        "bar_end": (192, 38, 211),
        "accent": (249, 168, 212),
        "glow": (236, 72, 153)
    },
    "ice_cyan": {
        "name": "Arctic Frost",
        "bar_start": (45, 212, 191),
        "bar_end": (8, 145, 178),
        "accent": (153, 246, 228),
        "glow": (20, 184, 166)
    }
}

TEMPLATES = {
    "bento": "Bento Pro Grid (1100x360)",
    "cyber": "Cyberpunk Hex HUD (1120x340)",
    "prism": "Triangle Prism Split (1060x370)",
    "square": "Compact Square Box (800x470)",
    "banner": "Ultra-Wide Strip (1200x250)",
    "exec": "Executive Ring Gauge (1080x360)"
}


# ==============================================================================
# FONT & IMAGE UTILITIES
# ==============================================================================
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


def fetch_image(url_or_path: str, size: tuple = None):
    if not url_or_path:
        return None
    img = None
    try:
        s = str(url_or_path).strip()
        if s.startswith("http"):
            r = requests.get(s, headers={"User-Agent": "Mozilla/5.0"}, timeout=2.5)
            if r.status_code == 200:
                img = Image.open(io.BytesIO(r.content)).convert("RGBA")
        elif os.path.exists(s):
            img = Image.open(s).convert("RGBA")
        if img and size:
            img = img.resize(size, Image.Resampling.LANCZOS)
    except Exception:
        return None
    return img


def create_smooth_mask(size, radius: int):
    scale = 4
    w, h = size[0] * scale, size[1] * scale
    mask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, w, h], radius=radius * scale, fill=255)
    return mask.resize(size, Image.Resampling.LANCZOS)


def create_polygon_mask(size, points: list):
    scale = 4
    w, h = size[0] * scale, size[1] * scale
    mask = Image.new("L", (w, h), 0)
    scaled_pts = [(int(px * scale), int(py * scale)) for px, py in points]
    ImageDraw.Draw(mask).polygon(scaled_pts, fill=255)
    return mask.resize(size, Image.Resampling.LANCZOS)


def get_regular_polygon(cx: float, cy: float, radius: float, sides: int, rotation_deg: float = 0):
    pts = []
    for i in range(sides):
        ang = math.radians((360 / sides) * i + rotation_deg)
        pts.append((cx + radius * math.cos(ang), cy + radius * math.sin(ang)))
    return pts


def create_gradient(width: int, height: int, c1, c2, vertical: bool = False):
    width = max(1, int(width))
    height = max(1, int(height))
    grad = Image.new("RGBA", (width, height))
    draw = ImageDraw.Draw(grad)
    steps = height if vertical else width
    for i in range(steps):
        t = i / max(steps - 1, 1)
        r = int(c1[0] + (c2[0] - c1[0]) * t)
        g = int(c1[1] + (c2[1] - c1[1]) * t)
        b = int(c1[2] + (c2[2] - c1[2]) * t)
        if vertical:
            draw.line([(0, i), (width, i)], fill=(r, g, b, 255))
        else:
            draw.line([(i, 0), (i, height)], fill=(r, g, b, 255))
    return grad


def format_number(n: int) -> str:
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}K"
    return str(n)


def get_tier_label(level: int, prestige: int) -> str:
    if prestige > 0:
        return f"PRESTIGE {prestige}"
    if level >= 50:
        return "IMMORTAL"
    if level >= 25:
        return "VETERAN TIER"
    if level >= 10:
        return "ELITE MEMBER"
    if level >= 5:
        return "RISING STAR"
    return "STARTER TIER" if level == 0 else f"TIER {level // 5 + 1}"


def paste_shaped_avatar(
    card: Image.Image,
    av_img: Image.Image,
    x: int,
    y: int,
    size: int,
    shape: str,
    theme: dict,
    status: str = "online"
):
    draw = ImageDraw.Draw(card)
    cx, cy = x + size // 2, y + size // 2

    if shape == "hexagon":
        outer = get_regular_polygon(cx, cy, size // 2 + 6, 6, -30)
        inner_local = get_regular_polygon(size // 2, size // 2, size // 2, 6, -30)
        draw.polygon(outer, fill=theme["accent"])
        mask = create_polygon_mask((size, size), inner_local)
        card.paste(av_img, (x, y), mask)
    elif shape == "diamond":
        outer = get_regular_polygon(cx, cy, size // 2 + 7, 4, 0)
        inner_local = get_regular_polygon(size // 2, size // 2, size // 2, 4, 0)
        draw.polygon(outer, fill=theme["bar_start"])
        mask = create_polygon_mask((size, size), inner_local)
        card.paste(av_img, (x, y), mask)
    elif shape == "square":
        draw.rectangle([x - 5, y - 5, x + size + 5, y + size + 5], fill=theme["accent"])
        draw.rectangle([x - 2, y - 2, x + size + 2, y + size + 2], fill=(15, 17, 24, 255))
        card.paste(av_img, (x, y))
    elif shape == "rounded":
        ring_pad = 5
        r_sz = size + ring_pad * 2
        r_grad = create_gradient(r_sz, r_sz, theme["bar_start"], theme["bar_end"])
        r_mask = create_smooth_mask((r_sz, r_sz), 28)
        card.paste(r_grad, (x - ring_pad, y - ring_pad), r_mask)
        av_mask = create_smooth_mask((size, size), 24)
        card.paste(av_img, (x, y), av_mask)
    else:
        ring_pad = 5
        r_sz = size + ring_pad * 2
        r_grad = create_gradient(r_sz, r_sz, theme["bar_start"], theme["bar_end"])
        r_mask = create_smooth_mask((r_sz, r_sz), r_sz // 2)
        card.paste(r_grad, (x - ring_pad, y - ring_pad), r_mask)

        gap_pad = 2
        g_sz = size + gap_pad * 2
        g_img = Image.new("RGBA", (g_sz, g_sz), (18, 20, 28, 255))
        g_mask = create_smooth_mask((g_sz, g_sz), g_sz // 2)
        card.paste(g_img, (x - gap_pad, y - gap_pad), g_mask)

        av_mask = create_smooth_mask((size, size), size // 2)
        card.paste(av_img, (x, y), av_mask)

    status_map = {
        "online": (34, 197, 94),
        "idle": (245, 158, 11),
        "dnd": (239, 68, 68),
        "offline": (107, 114, 128)
    }
    st_col = status_map.get(str(status).lower(), (34, 197, 94))
    draw = ImageDraw.Draw(card)
    ds = max(22, size // 5)
    dx, dy = x + size - ds - 4, y + size - ds - 4
    if shape == "square":
        draw.rectangle([dx - 3, dy - 3, dx + ds + 3, dy + ds + 3], fill=(18, 20, 28, 255))
        draw.rectangle([dx, dy, dx + ds, dy + ds], fill=st_col)
    else:
        draw.ellipse([dx - 4, dy - 4, dx + ds + 4, dy + ds + 4], fill=(18, 20, 28, 255))
        draw.ellipse([dx, dy, dx + ds, dy + ds], fill=st_col)


def draw_circular_gauge(card: Image.Image, cx: int, cy: int, radius: int, thickness: int, ratio: float, theme: dict, top_text: str, sub_text: str):
    scale = 3
    box_sz = (radius * 2 + 20) * scale
    layer = Image.new("RGBA", (box_sz, box_sz), (0, 0, 0, 0))
    ldraw = ImageDraw.Draw(layer)
    pad = 10 * scale
    bbox = [pad, pad, box_sz - pad, box_sz - pad]

    ldraw.arc(bbox, start=135, end=405, fill=(30, 35, 50, 255), width=thickness * scale)
    sweep = int(270 * min(max(ratio, 0.02), 1.0))
    ldraw.arc(bbox, start=135, end=135 + sweep, fill=theme["bar_start"], width=thickness * scale)

    smooth = layer.resize((radius * 2 + 20, radius * 2 + 20), Image.Resampling.LANCZOS)
    card.alpha_composite(smooth, (cx - radius - 10, cy - radius - 10))

    draw = ImageDraw.Draw(card)
    f_big = load_font(28, bold=True)
    f_sm = load_font(13, bold=True)
    b1 = draw.textbbox((0, 0), top_text, font=f_big)
    b2 = draw.textbbox((0, 0), sub_text, font=f_sm)
    draw.text((cx - (b1[2] - b1[0]) // 2, cy - 20), top_text, fill=(255, 255, 255), font=f_big)
    draw.text((cx - (b2[2] - b2[0]) // 2, cy + 14), sub_text, fill=theme["accent"], font=f_sm)


def build_base_canvas(
    card_w: int,
    card_h: int,
    theme: dict,
    bg_url: str = None,
    draw_outer_border: bool = True,
    bg_blur: int = 3,
    bg_dim: int = 195
):
    bg_img = fetch_image(bg_url, (card_w, card_h))

    if bg_img:
        if bg_blur > 0:
            bg_img = bg_img.filter(ImageFilter.GaussianBlur(radius=min(max(bg_blur, 0), 15)))
        dim_alpha = min(max(int(bg_dim), 80), 235)
        overlay = Image.new("RGBA", (card_w, card_h), (9, 10, 15, dim_alpha))
        card = Image.alpha_composite(bg_img, overlay)
    else:
        card = Image.new("RGBA", (card_w, card_h), (11, 12, 17, 255))
        glow = Image.new("RGBA", (card_w, card_h), (0, 0, 0, 0))
        gdraw = ImageDraw.Draw(glow)
        gc = theme["glow"]
        gdraw.ellipse([card_w - 340, -140, card_w + 120, 260], fill=(gc[0], gc[1], gc[2], 60))
        gdraw.ellipse([-120, card_h - 220, 280, card_h + 120], fill=(gc[0], gc[1], gc[2], 45))
        glow = glow.filter(ImageFilter.GaussianBlur(radius=65))
        card = Image.alpha_composite(card, glow)

    draw = ImageDraw.Draw(card)
    if draw_outer_border:
        draw.rounded_rectangle(
            [10, 10, card_w - 10, card_h - 10],
            radius=28,
            fill=(16, 18, 25, 185 if not bg_img else 130),
            outline=theme["accent"],
            width=2
        )
    return card, draw


def save_temp_card(card: Image.Image, prefix: str = "card") -> str:
    os.makedirs("bot/data", exist_ok=True)
    out_path = f"bot/data/{prefix}_{uuid.uuid4().hex[:8]}.png"
    card.convert("RGB").save(out_path, quality=95)
    return out_path


# ==============================================================================
# 1. MULTI-ARCHITECTURE RANK CARD (6 COMPLETELY DIFFERENT TEMPLATES & SIZES)
# ==============================================================================
def create_rank_card(
    display_name: str,
    username: str,
    level: int,
    current_xp: int,
    max_xp: int,
    rank_pos: int = 1,
    total_xp: int = 0,
    messages_count: int = 0,
    voice_minutes: int = 0,
    streak: int = 0,
    prestige: int = 0,
    bio: str = "Active Server Member",
    avatar_url: str = None,
    status: str = "online",
    bg_url: str = None,
    theme_name: str = "crimson",
    card_style: str = "bento",
    avatar_shape: str = "auto",
    bg_blur: int = 3,
    bg_dim: int = 190
) -> str:
    theme = THEMES.get(theme_name, THEMES["crimson"])
    ratio = min(max(current_xp / max(max_xp, 1), 0.0), 1.0)
    pct = int(ratio * 100)
    tier_text = get_tier_label(level, prestige)

    default_shapes = {
        "bento": "circle",
        "cyber": "hexagon",
        "prism": "diamond",
        "square": "square",
        "banner": "rounded",
        "exec": "circle"
    }
    actual_shape = default_shapes.get(card_style, "circle") if avatar_shape in [None, "auto"] else avatar_shape

    # ------------------------------------------------------------------
    # TEMPLATE A: "square" -> COMPACT NEO-BRUTALIST SQUARE BOX (800 x 470)
    # ------------------------------------------------------------------
    if card_style == "square":
        card_w, card_h = 800, 470
        card, draw = build_base_canvas(card_w, card_h, theme, bg_url, draw_outer_border=False, bg_blur=bg_blur, bg_dim=bg_dim)

        draw.rectangle([8, 8, card_w - 8, card_h - 8], fill=(14, 16, 22, 215 if not bg_url else 150), outline=theme["accent"], width=3)
        banner_grad = create_gradient(card_w - 24, 110, theme["bar_start"], theme["bar_end"])
        card.paste(banner_grad, (12, 12))
        draw = ImageDraw.Draw(card)
        draw.polygon([(card_w - 140, 12), (card_w - 12, 12), (card_w - 12, 122), (card_w - 70, 122)], fill=(10, 12, 18, 120))

        f_hdr = load_font(14, bold=True)
        f_big = load_font(34, bold=True)
        draw.rectangle([480, 26, 615, 104], fill=(14, 16, 24, 235), outline=theme["accent"], width=2)
        draw.text((495, 32), "LEVEL", fill=(160, 170, 185), font=f_hdr)
        draw.text((495, 52), str(level), fill=theme["accent"], font=f_big)

        draw.rectangle([630, 26, 768, 104], fill=(14, 16, 24, 235), outline=(255, 255, 255, 80), width=2)
        draw.text((645, 32), "RANK", fill=(160, 170, 185), font=f_hdr)
        draw.text((645, 52), f"#{rank_pos}", fill=(255, 255, 255), font=f_big)

        av_size = 136
        av_img = fetch_image(avatar_url, (av_size, av_size)) or Image.new("RGBA", (av_size, av_size), (45, 50, 65, 255))
        paste_shaped_avatar(card, av_img, 38, 54, av_size, actual_shape, theme, status)
        draw = ImageDraw.Draw(card)

        draw.text((200, 132), str(display_name)[:18], fill=(255, 255, 255), font=load_font(34, bold=True))
        draw.text((200, 174), f"@{username}  •  {tier_text}", fill=theme["accent"], font=load_font(16, bold=True))
        draw.text((38, 212), f"\" {str(bio)[:48]} \"", fill=(185, 195, 210), font=load_font(16, bold=True))

        stats = [
            ("MESSAGES SENT", format_number(messages_count)),
            ("VOICE ACTIVITY", f"{voice_minutes} MINS"),
            ("DAILY STREAK", f"{streak} DAYS"),
            ("LIFETIME XP", f"{format_number(total_xp)} XP")
        ]
        for idx, (lbl, val) in enumerate(stats):
            r, c = idx // 2, idx % 2
            bx = 38 + c * 368
            by = 250 + r * 62
            draw.rectangle([bx, by, bx + 354, by + 50], fill=(22, 26, 36, 230), outline=(255, 255, 255, 35), width=1)
            draw.rectangle([bx, by, bx + 6, by + 50], fill=theme["bar_start"])
            draw.text((bx + 20, by + 15), lbl, fill=(148, 163, 184), font=load_font(14, bold=True))
            vb = draw.textbbox((0, 0), val, font=load_font(18, bold=True))
            draw.text((bx + 338 - (vb[2] - vb[0]), by + 13), val, fill=(255, 255, 255), font=load_font(18, bold=True))

        draw.text((38, 384), f"XP PROGRESS: {current_xp:,} / {max_xp:,} XP", fill=(255, 255, 255), font=load_font(15, bold=True))
        pct_txt = f"{pct}% COMPLETED"
        pb = draw.textbbox((0, 0), pct_txt, font=load_font(15, bold=True))
        draw.text((762 - (pb[2] - pb[0]), 384), pct_txt, fill=theme["accent"], font=load_font(15, bold=True))

        blocks = 20
        active_blocks = int(round(ratio * blocks))
        bx_start = 38
        by_bar = 412
        bw = 31
        gap = 5
        for b in range(blocks):
            x0 = bx_start + b * (bw + gap)
            col = theme["bar_start"] if b < active_blocks else (28, 32, 44, 255)
            draw.rectangle([x0, by_bar, x0 + bw, by_bar + 32], fill=col, outline=(255, 255, 255, 25))

        return save_temp_card(card, "rank_sq")

    # ------------------------------------------------------------------
    # TEMPLATE B: "cyber" -> CYBERPUNK HEX HUD (1120 x 340, Right Avatar)
    # ------------------------------------------------------------------
    if card_style == "cyber":
        card_w, card_h = 1120, 340
        card, draw = build_base_canvas(card_w, card_h, theme, bg_url, draw_outer_border=False, bg_blur=bg_blur, bg_dim=bg_dim)

        pts = [(40, 10), (card_w - 10, 10), (card_w - 10, card_h - 40), (card_w - 40, card_h - 10), (10, card_h - 10), (10, 40)]
        draw.polygon(pts, fill=(12, 15, 23, 210 if not bg_url else 145), outline=theme["accent"])
        draw.polygon([(10, 10), (55, 10), (10, 55)], fill=theme["bar_start"])
        draw.polygon([(card_w - 10, card_h - 10), (card_w - 55, card_h - 10), (card_w - 10, card_h - 55)], fill=theme["bar_start"])

        draw.polygon([(55, 24), (420, 24), (400, 54), (35, 54)], fill=(24, 28, 42, 240), outline=theme["accent"])
        draw.text((52, 30), f"CYBER-OS // {tier_text} // RANK #{rank_pos}", fill=theme["accent"], font=load_font(14, bold=True))

        draw.text((40, 68), str(display_name)[:18].upper(), fill=(255, 255, 255), font=load_font(42, bold=True))
        draw.text((42, 118), f"@{username}   //   \"{str(bio)[:38]}\"", fill=(165, 175, 195), font=load_font(17, bold=True))

        stats = [
            ("LEVEL", str(level)),
            ("RANK", f"#{rank_pos}"),
            ("MSGS", format_number(messages_count)),
            ("VOICE", f"{voice_minutes}m"),
            ("STREAK", f"{streak}d")
        ]
        sx = 40
        sy = 160
        for idx, (lbl, val) in enumerate(stats):
            pw = 142
            ph = 66
            poly = [(sx + 14, sy), (sx + pw, sy), (sx + pw - 14, sy + ph), (sx, sy + ph)]
            draw.polygon(poly, fill=(22, 26, 38, 235), outline=theme["accent"] if idx < 2 else (255, 255, 255, 35))
            draw.text((sx + 22, sy + 10), lbl, fill=(140, 150, 170), font=load_font(12, bold=True))
            draw.text((sx + 20, sy + 28), val, fill=theme["accent"] if idx == 0 else (255, 255, 255), font=load_font(22, bold=True))
            sx += pw + 12

        bx, by, bw, bh = 40, 254, 770, 48
        track_poly = [(bx + 18, by), (bx + bw, by), (bx + bw - 18, by + bh), (bx, by + bh)]
        draw.polygon(track_poly, fill=(20, 23, 34, 255), outline=theme["accent"])
        if ratio > 0:
            fw = max(int((bw - 24) * ratio), 30)
            fill_poly = [(bx + 20, by + 6), (bx + 20 + fw, by + 6), (bx + 6 + fw, by + bh - 6), (bx + 6, by + bh - 6)]
            draw.polygon(fill_poly, fill=theme["bar_start"])

        xp_txt = f"EXP: {current_xp:,} / {max_xp:,} ({pct}%)"
        draw.text((bx + 32, by + 13), xp_txt, fill=(255, 255, 255), font=load_font(18, bold=True))

        av_size = 190
        av_img = fetch_image(avatar_url, (av_size, av_size)) or Image.new("RGBA", (av_size, av_size), (45, 50, 65, 255))
        paste_shaped_avatar(card, av_img, 865, 62, av_size, actual_shape, theme, status)
        draw = ImageDraw.Draw(card)
        draw.text((895, 272), f"TOTAL: {format_number(total_xp)} XP", fill=theme["accent"], font=load_font(15, bold=True))

        return save_temp_card(card, "rank_cyber")

    # ------------------------------------------------------------------
    # TEMPLATE C: "prism" -> TRIANGLE PRISM GEOMETRIC SPLIT (1060 x 370)
    # ------------------------------------------------------------------
    if card_style == "prism":
        card_w, card_h = 1060, 370
        card, draw = build_base_canvas(card_w, card_h, theme, bg_url, draw_outer_border=False, bg_blur=bg_blur, bg_dim=bg_dim)

        poly_layer = Image.new("RGBA", (card_w, card_h), (0, 0, 0, 0))
        pdraw = ImageDraw.Draw(poly_layer)
        c1, c2 = theme["bar_start"], theme["bar_end"]
        pdraw.polygon([(0, 0), (380, 0), (210, card_h), (0, card_h)], fill=(c1[0], c1[1], c1[2], 55))
        pdraw.polygon([(380, 0), (430, 0), (260, card_h), (210, card_h)], fill=(c2[0], c2[1], c2[2], 95))
        pdraw.polygon([(card_w - 180, 0), (card_w, 0), (card_w, 180)], fill=(c1[0], c1[1], c1[2], 45))
        card = Image.alpha_composite(card, poly_layer)
        draw = ImageDraw.Draw(card)

        draw.rounded_rectangle([10, 10, card_w - 10, card_h - 10], radius=22, outline=theme["accent"], width=2)

        av_size = 176
        av_img = fetch_image(avatar_url, (av_size, av_size)) or Image.new("RGBA", (av_size, av_size), (45, 50, 65, 255))
        paste_shaped_avatar(card, av_img, 62, 54, av_size, actual_shape, theme, status)
        draw = ImageDraw.Draw(card)

        draw.polygon([(55, 265), (245, 265), (260, 285), (245, 305), (55, 305), (40, 285)], fill=(20, 24, 36, 245), outline=theme["accent"])
        tb = draw.textbbox((0, 0), tier_text, font=load_font(14, bold=True))
        draw.text((150 - (tb[2] - tb[0]) // 2, 276), tier_text, fill=theme["accent"], font=load_font(14, bold=True))

        ix = 340
        draw.text((ix, 36), str(display_name)[:17], fill=(255, 255, 255), font=load_font(42, bold=True))
        draw.text((ix, 88), f"@{username}   •   \"{str(bio)[:36]}\"", fill=(180, 190, 210), font=load_font(17, bold=True))

        prism_stats = [
            ("LEVEL", str(level)),
            ("RANK", f"#{rank_pos}"),
            ("MESSAGES", format_number(messages_count)),
            ("VOICE", f"{voice_minutes}m"),
            ("STREAK", f"{streak}d")
        ]
        px = ix
        py = 138
        for idx, (lbl, val) in enumerate(prism_stats):
            bw, bh = 126, 82
            draw.rounded_rectangle([px, py, px + bw, py + bh], radius=14, fill=(20, 24, 36, 230), outline=theme["accent"] if idx < 2 else (255, 255, 255, 30), width=1)
            draw.polygon([(px + bw - 24, py), (px + bw, py), (px + bw, py + 24)], fill=theme["bar_start"])
            draw.text((px + 14, py + 14), lbl, fill=(148, 163, 184), font=load_font(12, bold=True))
            draw.text((px + 14, py + 38), val, fill=(255, 255, 255) if idx != 0 else theme["accent"], font=load_font(24, bold=True))
            px += bw + 12

        bar_x, bar_y, bar_w, bar_h = ix, 268, 678, 52
        pts_track = [(bar_x, bar_y + bar_h // 2), (bar_x + 20, bar_y), (bar_x + bar_w - 20, bar_y), (bar_x + bar_w, bar_y + bar_h // 2), (bar_x + bar_w - 20, bar_y + bar_h), (bar_x + 20, bar_y + bar_h)]
        draw.polygon(pts_track, fill=(20, 23, 34, 255), outline=theme["accent"])

        if ratio > 0:
            fw = max(int((bar_w - 24) * ratio), 40)
            pts_fill = [(bar_x + 10, bar_y + bar_h // 2), (bar_x + 24, bar_y + 6), (bar_x + fw - 10, bar_y + 6), (bar_x + fw + 4, bar_y + bar_h // 2), (bar_x + fw - 10, bar_y + bar_h - 6), (bar_x + 24, bar_y + bar_h - 6)]
            draw.polygon(pts_fill, fill=theme["bar_start"])

        draw.text((bar_x + 30, bar_y + 15), f"{current_xp:,} / {max_xp:,} XP", fill=(255, 255, 255), font=load_font(18, bold=True))
        pt = f"{pct}%"
        pb = draw.textbbox((0, 0), pt, font=load_font(18, bold=True))
        draw.text((bar_x + bar_w - (pb[2] - pb[0]) - 30, bar_y + 15), pt, fill=(255, 255, 255), font=load_font(18, bold=True))

        return save_temp_card(card, "rank_prism")

    # ------------------------------------------------------------------
    # TEMPLATE D: "banner" -> ULTRA-WIDE CINEMATIC STRIP (1200 x 250)
    # ------------------------------------------------------------------
    if card_style == "banner":
        card_w, card_h = 1200, 250
        card, draw = build_base_canvas(card_w, card_h, theme, bg_url, draw_outer_border=False, bg_blur=bg_blur, bg_dim=bg_dim)

        draw.rounded_rectangle([8, 8, card_w - 8, card_h - 8], radius=24, fill=(14, 16, 24, 180 if bg_url else 215), outline=theme["accent"], width=2)

        f_wm = load_font(130, bold=True)
        draw.text((card_w - 430, 15), f"LV.{level}", fill=(255, 255, 255, 18), font=f_wm)

        av_size = 156
        av_img = fetch_image(avatar_url, (av_size, av_size)) or Image.new("RGBA", (av_size, av_size), (45, 50, 65, 255))
        paste_shaped_avatar(card, av_img, 36, 36, av_size, actual_shape, theme, status)
        draw = ImageDraw.Draw(card)

        ix = 222
        draw.text((ix, 32), str(display_name)[:20], fill=(255, 255, 255), font=load_font(38, bold=True))
        draw.text((ix, 80), f"@{username}  •  {tier_text}  •  \"{str(bio)[:40]}\"", fill=theme["accent"], font=load_font(16, bold=True))

        pills = [
            ("RANK", f"#{rank_pos}"),
            ("LEVEL", str(level)),
            ("MESSAGES", format_number(messages_count)),
            ("VOICE", f"{voice_minutes}m"),
            ("STREAK", f"{streak}d"),
            ("TOTAL XP", format_number(total_xp))
        ]
        px = ix
        for lbl, val in pills:
            txt = f"{lbl}: {val}"
            b = draw.textbbox((0, 0), txt, font=load_font(15, bold=True))
            pw = (b[2] - b[0]) + 30
            draw.rounded_rectangle([px, 124, px + pw, 164], radius=10, fill=(24, 28, 40, 235), outline=(255, 255, 255, 30), width=1)
            draw.text((px + 15, 134), txt, fill=(235, 240, 250), font=load_font(15, bold=True))
            px += pw + 10

        bx, by, bw, bh = 36, 198, card_w - 72, 26
        draw.rounded_rectangle([bx, by, bx + bw, by + bh], radius=13, fill=(22, 25, 36, 255), outline=(255, 255, 255, 25))
        if ratio > 0:
            fw = max(int(bw * ratio), 26)
            grad = create_gradient(fw, bh, theme["bar_start"], theme["bar_end"])
            mask = create_smooth_mask((fw, bh), 13)
            card.paste(grad, (bx, by), mask)
            draw = ImageDraw.Draw(card)

        draw.text((bx + 16, by + 3), f"{current_xp:,} / {max_xp:,} XP ({pct}%)", fill=(255, 255, 255), font=load_font(14, bold=True))
        return save_temp_card(card, "rank_banner")

    # ------------------------------------------------------------------
    # TEMPLATE E: "exec" -> EXECUTIVE CIRCULAR GAUGE CARD (1080 x 360)
    # ------------------------------------------------------------------
    if card_style == "exec":
        card_w, card_h = 1080, 360
        card, draw = build_base_canvas(card_w, card_h, theme, bg_url, draw_outer_border=True, bg_blur=bg_blur, bg_dim=bg_dim)

        av_size = 168
        av_img = fetch_image(avatar_url, (av_size, av_size)) or Image.new("RGBA", (av_size, av_size), (45, 50, 65, 255))
        paste_shaped_avatar(card, av_img, 46, 52, av_size, actual_shape, theme, status)
        draw = ImageDraw.Draw(card)

        draw.rounded_rectangle([46, 244, 214, 282], radius=10, fill=(26, 30, 44, 240), outline=theme["accent"], width=1)
        tb = draw.textbbox((0, 0), tier_text, font=load_font(13, bold=True))
        draw.text((130 - (tb[2] - tb[0]) // 2, 255), tier_text, fill=theme["accent"], font=load_font(13, bold=True))

        ix = 250
        draw.text((ix, 42), str(display_name)[:18], fill=(255, 255, 255), font=load_font(40, bold=True))
        draw.text((ix, 92), f"@{username}   •   RANK #{rank_pos}   •   LEVEL {level}", fill=theme["accent"], font=load_font(18, bold=True))
        draw.text((ix, 126), f"\" {str(bio)[:42]} \"", fill=(175, 185, 205), font=load_font(16, bold=True))

        estats = [
            ("CHAT MESSAGES", format_number(messages_count)),
            ("VOICE TIME", f"{voice_minutes} MINS"),
            ("ACTIVE STREAK", f"{streak} DAYS"),
            ("TOTAL XP EARNED", format_number(total_xp))
        ]
        for idx, (lbl, val) in enumerate(estats):
            r, c = idx // 2, idx % 2
            bx = ix + c * 255
            by = 172 + r * 72
            draw.rounded_rectangle([bx, by, bx + 240, by + 60], radius=14, fill=(24, 28, 40, 235), outline=(255, 255, 255, 25), width=1)
            draw.text((bx + 16, by + 10), lbl, fill=(145, 155, 175), font=load_font(12, bold=True))
            draw.text((bx + 16, by + 28), val, fill=(255, 255, 255), font=load_font(20, bold=True))

        draw.rounded_rectangle([785, 34, 1044, card_h - 34], radius=24, fill=(20, 24, 36, 235), outline=theme["accent"], width=1)
        draw_circular_gauge(card, 914, 155, 86, 14, ratio, theme, f"{pct}%", f"LVL {level}")
        draw = ImageDraw.Draw(card)
        xp_line = f"{current_xp:,} / {max_xp:,} XP"
        xb = draw.textbbox((0, 0), xp_line, font=load_font(16, bold=True))
        draw.text((914 - (xb[2] - xb[0]) // 2, 268), xp_line, fill=(220, 230, 245), font=load_font(16, bold=True))
        draw.text((862, 294), "NEXT LEVEL PROGRESS", fill=(135, 145, 165), font=load_font(11, bold=True))

        return save_temp_card(card, "rank_exec")

    # ------------------------------------------------------------------
    # TEMPLATE F: "bento" (DEFAULT) -> BENTO PRO GRID (1100 x 360)
    # ------------------------------------------------------------------
    card_w, card_h = 1100, 360
    card, draw = build_base_canvas(card_w, card_h, theme, bg_url, draw_outer_border=True, bg_blur=bg_blur, bg_dim=bg_dim)

    draw.rounded_rectangle(
        [26, 26, 276, card_h - 26],
        radius=24,
        fill=(22, 25, 35, 230),
        outline=(255, 255, 255, 22),
        width=1
    )

    f_name = load_font(42, bold=True)
    f_user = load_font(20, bold=False)
    f_bio = load_font(17, bold=True)
    f_label = load_font(14, bold=True)
    f_stat = load_font(16, bold=True)
    f_lvl = load_font(48, bold=True)
    f_rank = load_font(52, bold=True)
    f_xp = load_font(21, bold=True)

    av_size = 176
    av_x, av_y = 63, 44
    av_img = fetch_image(avatar_url, (av_size, av_size)) or Image.new("RGBA", (av_size, av_size), (45, 50, 65, 255))
    paste_shaped_avatar(card, av_img, av_x, av_y, av_size, actual_shape, theme, status)
    draw = ImageDraw.Draw(card)

    tb = draw.textbbox((0, 0), tier_text, font=f_label)
    tw = tb[2] - tb[0]
    draw.rounded_rectangle(
        [151 - (tw // 2) - 18, 246, 151 + (tw // 2) + 18, 282],
        radius=12,
        fill=(30, 34, 48, 255),
        outline=theme["accent"],
        width=1
    )
    draw.text((151 - (tw // 2), 255), tier_text, fill=theme["accent"], font=f_label)

    info_x = 305
    draw.text((info_x, 36), str(display_name)[:17], fill=(255, 255, 255), font=f_name)
    draw.text((info_x, 88), f"@{username}", fill=(148, 163, 184), font=f_user)
    draw.text((info_x, 120), f"\" {str(bio)[:42]} \"", fill=theme["accent"], font=f_bio)

    draw.rounded_rectangle([705, 34, 865, 142], radius=20, fill=(24, 27, 38, 240), outline=theme["accent"], width=1)
    draw.text((725, 46), "LEVEL", fill=(148, 163, 184), font=f_label)
    draw.text((725, 68), str(level), fill=theme["accent"], font=f_lvl)

    draw.rounded_rectangle([880, 34, 1068, 142], radius=20, fill=(24, 27, 38, 240), outline=theme["accent"], width=1)
    draw.text((902, 46), "SERVER RANK", fill=(148, 163, 184), font=f_label)
    draw.text((902, 66), f"#{rank_pos}", fill=(255, 255, 255), font=f_rank)

    chips = [
        ("MSGS", format_number(messages_count)),
        ("VOICE", f"{voice_minutes}m"),
        ("STREAK", f"{streak}d"),
        ("TOTAL XP", format_number(total_xp))
    ]
    chip_x = info_x
    chip_y = 162
    for label_part, val_part in chips:
        full_str = f"{label_part}: {val_part}"
        cb = draw.textbbox((0, 0), full_str, font=f_stat)
        cw = (cb[2] - cb[0]) + 32
        draw.rounded_rectangle(
            [chip_x, chip_y, chip_x + cw, chip_y + 38],
            radius=12,
            fill=(24, 27, 38, 230),
            outline=(255, 255, 255, 20),
            width=1
        )
        draw.text((chip_x + 16, chip_y + 9), full_str, fill=(226, 232, 240), font=f_stat)
        chip_x += cw + 12

    bar_x = info_x
    bar_y = 252
    bar_w = card_w - bar_x - 32
    bar_h = 62

    draw.text((bar_x + 4, bar_y - 26), "E X P E R I E N C E", fill=(160, 170, 185), font=f_label)

    pct_str = f"{pct}% COMPLETED"
    pb = draw.textbbox((0, 0), pct_str, font=f_label)
    draw.text((bar_x + bar_w - (pb[2] - pb[0]) - 4, bar_y - 26), pct_str, fill=theme["accent"], font=f_label)

    track_img = Image.new("RGBA", (bar_w, bar_h), (23, 25, 34, 255))
    track_mask = create_smooth_mask((bar_w, bar_h), bar_h // 2)
    card.paste(track_img, (bar_x, bar_y), track_mask)

    pad = 8
    inner_max_w = bar_w - (pad * 2)
    inner_h = bar_h - (pad * 2)

    if max_xp > 0 and current_xp > 0:
        fill_w = max(int(inner_max_w * ratio), inner_h)
        grad_bar = create_gradient(fill_w, inner_h, theme["bar_start"], theme["bar_end"])
        fill_mask = create_smooth_mask((fill_w, inner_h), inner_h // 2)
        card.paste(grad_bar, (bar_x + pad, bar_y + pad), fill_mask)

    draw = ImageDraw.Draw(card)
    draw.rounded_rectangle(
        [bar_x, bar_y, bar_x + bar_w, bar_y + bar_h],
        radius=bar_h // 2,
        outline=(255, 255, 255, 24),
        width=1
    )

    xp_str = f"{current_xp:,} / {max_xp:,} XP"
    xb = draw.textbbox((0, 0), xp_str, font=f_xp)
    xw = xb[2] - xb[0]
    xh = xb[3] - xb[1]
    draw.text(
        (bar_x + bar_w - xw - 24, bar_y + (bar_h - xh) // 2 - 2),
        xp_str,
        fill=(255, 255, 255),
        font=f_xp
    )

    return save_temp_card(card, "rank")


# ==============================================================================
# 2. LEADERBOARD CARD (CHAMFERED ROWS + HEX/DIAMOND RANK SHIELDS + MINI XP BARS)
# ==============================================================================
def create_leaderboard_card(
    guild_name: str,
    mode_title: str,
    entries: list,
    page: int,
    max_pages: int,
    multiplier: float = 1.0,
    theme_name: str = "crimson",
    bg_url: str = None
) -> str:
    rows_count = max(len(entries), 1)
    card_w = 1060
    card_h = 175 + (rows_count * 78) + 35
    theme = THEMES.get(theme_name, THEMES["crimson"])
    card, draw = build_base_canvas(card_w, card_h, theme, bg_url)

    f_title = load_font(32, bold=True)
    f_sub = load_font(16, bold=True)
    f_rank = load_font(20, bold=True)
    f_name = load_font(22, bold=True)
    f_meta = load_font(15, bold=True)
    f_lvl = load_font(20, bold=True)

    draw.text((40, 32), f"{guild_name[:24].upper()} — LEADERBOARD", fill=(255, 255, 255), font=f_title)
    draw.text((40, 74), f"FILTER: {mode_title.upper()}   •   PAGE {page}/{max_pages}   •   BOOST: {multiplier:.1f}X", fill=theme["accent"], font=f_sub)
    draw.line([(40, 110), (card_w - 40, 110)], fill=(255, 255, 255, 30), width=1)

    if not entries:
        draw.text((40, 145), "No leveling activity recorded yet. Start chatting to earn XP!", fill=(180, 190, 205), font=f_name)
        return save_temp_card(card, "leaderboard")

    y = 128
    for item in entries:
        rk = item["rank"]
        row_pts = [(50, y), (card_w - 36, y), (card_w - 36, y + 54), (card_w - 50, y + 66), (36, y + 66), (36, y + 12)]
        draw.polygon(row_pts, fill=(24, 27, 38, 235), outline=theme["accent"] if rk <= 3 else (255, 255, 255, 22))

        if rk == 1:
            badge_col = (251, 191, 36)
            text_col = (15, 15, 20)
        elif rk == 2:
            badge_col = (203, 213, 225)
            text_col = (15, 15, 20)
        elif rk == 3:
            badge_col = (217, 119, 6)
            text_col = (255, 255, 255)
        else:
            badge_col = (35, 39, 54)
            text_col = theme["accent"]

        draw.polygon([(58, y + 10), (114, y + 10), (124, y + 33), (114, y + 56), (58, y + 56), (48, y + 33)], fill=badge_col)
        rk_str = f"#{rk}"
        rb = draw.textbbox((0, 0), rk_str, font=f_rank)
        draw.text((86 - (rb[2] - rb[0]) // 2, y + 21), rk_str, fill=text_col, font=f_rank)

        p_tag = f" [P{item['prestige']}]" if item.get("prestige", 0) > 0 else ""
        draw.text((142, y + 19), f"{str(item['name'])[:18]}{p_tag}", fill=(255, 255, 255), font=f_name)

        meta_str = f"MSGS: {format_number(item['messages'])}   •   VOICE: {item['voice']}m   •   XP: {format_number(item['xp'])}/{format_number(item['max_xp'])}"
        draw.text((435, y + 14), meta_str, fill=(175, 185, 200), font=f_meta)

        mb_x, mb_y, mb_w, mb_h = 435, y + 42, 420, 8
        draw.rounded_rectangle([mb_x, mb_y, mb_x + mb_w, mb_y + mb_h], radius=4, fill=(15, 17, 24, 255))
        mxp = max(item.get("max_xp", 100), 1)
        cxp = min(max(item.get("xp", 0), 0), mxp)
        fill_mw = int(mb_w * (cxp / mxp))
        if fill_mw > 4:
            draw.rounded_rectangle([mb_x, mb_y, mb_x + fill_mw, mb_y + mb_h], radius=4, fill=theme["accent"])

        lvl_pill_w = 135
        lvl_x = card_w - 52 - lvl_pill_w
        draw.rounded_rectangle([lvl_x, y + 13, lvl_x + lvl_pill_w, y + 53], radius=10, fill=(32, 36, 50, 255), outline=theme["accent"], width=1)
        lvl_str = f"LVL {item['level']}"
        lb = draw.textbbox((0, 0), lvl_str, font=f_lvl)
        draw.text((lvl_x + (lvl_pill_w - (lb[2] - lb[0])) // 2, y + 21), lvl_str, fill=theme["accent"], font=f_lvl)

        y += 78

    return save_temp_card(card, "leaderboard")


# ==============================================================================
# 3. STATS DASHBOARD CARD (CIRCULAR GAUGE + CHAMFERED TECH MATRIX - 1080 x 450)
# ==============================================================================
def create_stats_card(
    display_name: str,
    username: str,
    avatar_url: str,
    stats_grid: list,
    theme_name: str = "crimson",
    bg_url: str = None,
    progress_ratio: float = 0.5
) -> str:
    card_w, card_h = 1080, 450
    theme = THEMES.get(theme_name, THEMES["crimson"])
    card, draw = build_base_canvas(card_w, card_h, theme, bg_url)

    f_title = load_font(32, bold=True)
    f_sub = load_font(16, bold=True)
    f_label = load_font(13, bold=True)
    f_val = load_font(23, bold=True)

    draw.rounded_rectangle([30, 30, 290, card_h - 30], radius=22, fill=(20, 24, 36, 235), outline=theme["accent"], width=1)

    av_size = 96
    av_img = fetch_image(avatar_url, (av_size, av_size)) or Image.new("RGBA", (av_size, av_size), (45, 50, 65, 255))
    paste_shaped_avatar(card, av_img, 112, 50, av_size, "hexagon", theme, "online")

    pct = int(min(max(progress_ratio, 0.0), 1.0) * 100)
    draw_circular_gauge(card, 160, 275, 76, 12, progress_ratio, theme, f"{pct}%", "LEVEL XP")
    draw = ImageDraw.Draw(card)
    draw.text((88, 378), "ANALYTICS CORE", fill=(148, 163, 184), font=f_label)

    draw.text((320, 36), f"{str(display_name)[:20].upper()} — ANALYTICS MATRIX", fill=(255, 255, 255), font=f_title)
    draw.text((320, 78), f"@{username}   •   LIVE SERVER TELEMETRY & ACTIVITY METRICS", fill=theme["accent"], font=f_sub)

    cols = 4
    box_w = 170
    box_h = 132
    start_x = 320
    start_y = 126
    gap_x = 14
    gap_y = 18

    for idx, (label, val) in enumerate(stats_grid[:8]):
        r = idx // cols
        c = idx % cols
        bx = start_x + c * (box_w + gap_x)
        by = start_y + r * (box_h + gap_y)

        pts = [(bx + 14, by), (bx + box_w, by), (bx + box_w, by + box_h - 14), (bx + box_w - 14, by + box_h), (bx, by + box_h), (bx, by + 14)]
        draw.polygon(pts, fill=(24, 27, 38, 235), outline=theme["accent"])
        draw.polygon([(bx + box_w - 22, by), (bx + box_w, by), (bx + box_w, by + 22)], fill=theme["bar_start"])

        draw.text((bx + 16, by + 24), str(label).upper(), fill=(148, 163, 184), font=f_label)
        draw.text((bx + 16, by + 62), str(val)[:13], fill=(255, 255, 255) if idx % 2 == 0 else theme["accent"], font=f_val)

    return save_temp_card(card, "stats")


# ==============================================================================
# 4. UNIVERSAL BANNER CARD (ASYMMETRIC ESPORTS NOTIFICATION BANNER - 960 x 260)
# ==============================================================================
def create_banner_card(
    title: str,
    subtitle: str,
    highlights: list = None,
    footer: str = "SOFIYA LEVELING SYSTEM",
    avatar_url: str = None,
    theme_name: str = "crimson",
    bg_url: str = None
) -> str:
    highlights = highlights or []
    card_w = 960
    card_h = 260 if len(highlights) <= 3 else 330
    theme = THEMES.get(theme_name, THEMES["crimson"])
    card, draw = build_base_canvas(card_w, card_h, theme, bg_url)

    draw.polygon([(10, 10), (85, 10), (10, 85)], fill=theme["bar_start"])
    draw.polygon([(card_w - 10, card_h - 10), (card_w - 65, card_h - 10), (card_w - 10, card_h - 65)], fill=theme["bar_end"])

    f_title = load_font(32, bold=True)
    f_sub = load_font(18, bold=False)
    f_label = load_font(13, bold=True)
    f_val = load_font(22, bold=True)
    f_foot = load_font(13, bold=True)

    text_x = 42
    if avatar_url:
        av_size = 112
        av_img = fetch_image(avatar_url, (av_size, av_size))
        if av_img:
            paste_shaped_avatar(card, av_img, 42, 42, av_size, "rounded", theme, "online")
            draw = ImageDraw.Draw(card)
            text_x = 180

    draw.text((text_x, 36), str(title).upper(), fill=theme["accent"], font=f_title)
    draw.text((text_x, 80), str(subtitle)[:68], fill=(230, 235, 245), font=f_sub)

    if highlights:
        chip_x = text_x
        chip_y = 130
        for lbl, val in highlights[:4]:
            val_b = draw.textbbox((0, 0), str(val), font=f_val)
            lbl_b = draw.textbbox((0, 0), str(lbl).upper(), font=f_label)
            box_w = max(val_b[2] - val_b[0], lbl_b[2] - lbl_b[0]) + 44
            pts = [(chip_x + 10, chip_y), (chip_x + box_w, chip_y), (chip_x + box_w, chip_y + 64), (chip_x + box_w - 10, chip_y + 74), (chip_x, chip_y + 74), (chip_x, chip_y + 10)]
            draw.polygon(pts, fill=(24, 27, 38, 240), outline=theme["accent"])
            draw.text((chip_x + 20, chip_y + 14), str(lbl).upper(), fill=(148, 163, 184), font=f_label)
            draw.text((chip_x + 20, chip_y + 34), str(val), fill=(255, 255, 255), font=f_val)
            chip_x += box_w + 16

    draw.text((text_x, card_h - 36), str(footer).upper(), fill=(110, 120, 138), font=f_foot)
    return save_temp_card(card, "banner")