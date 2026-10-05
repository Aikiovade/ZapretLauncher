"""A9/I3: генерация картинок мастера установщика.

Запуск: python tools/make_installer_art.py
Результат:
  installer/wizard_image.bmp   (328x628, 2x — крупная картинка мастера)
  installer/wizard_small.bmp   (110x110)
  installer/wizard_back.bmp    (800x600 — фон окна мастера, используется с opacity)
"""
import math
import os
import sys

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(ROOT, "installer")
BG_TOP = (10, 11, 30)
BG_BOTTOM = (16, 19, 46)
ACCENT = (0, 255, 136)
ACCENT_DIM = (0, 150, 85)
CYAN = (0, 220, 255)
MUTED = (90, 101, 145)
WHITE = (232, 236, 255)


def _font(size, bold=True):
    names = ("segoeuib.ttf", "seguisb.ttf", "arialbd.ttf") if bold else ("segoeui.ttf", "arial.ttf")
    for name in names:
        try:
            return ImageFont.truetype(name, size)
        except Exception:
            continue
    return ImageFont.load_default()


def _vgradient(img, top, bottom):
    w, h = img.size
    px = img.load()
    for y in range(h):
        t = y / max(h - 1, 1)
        color = tuple(int(top[i] + (bottom[i] - top[i]) * t) for i in range(3))
        for x in range(w):
            px[x, y] = color


def _grid(draw, w, h, step=26, color=(24, 28, 62)):
    for x in range(0, w, step):
        draw.line([(x, 0), (x, h)], fill=color, width=1)
    for y in range(0, h, step):
        draw.line([(0, y), (w, y)], fill=color, width=1)


def _glow(size, center, radius, color, alpha=90):
    layer = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    cx, cy = center
    draw.ellipse([cx - radius, cy - radius, cx + radius, cy + radius], fill=color + (alpha,))
    return layer.filter(ImageFilter.GaussianBlur(radius * 0.55))


def _centered(draw, width, y, text, font, fill):
    bbox = draw.textbbox((0, 0), text, font=font)
    x = (width - (bbox[2] - bbox[0])) // 2
    draw.text((x, y), text, font=font, fill=fill)


def make_wizard_image(path):
    w, h = 328, 628
    img = Image.new("RGB", (w, h), BG_TOP)
    _vgradient(img, BG_TOP, BG_BOTTOM)
    img = img.convert("RGBA")
    draw = ImageDraw.Draw(img)
    _grid(draw, w, h)
    img = Image.alpha_composite(img, _glow((w, h), (w // 2, 190), 130, ACCENT, 80))
    img = Image.alpha_composite(img, _glow((w, h), (w // 2, 470), 150, CYAN, 40))
    draw = ImageDraw.Draw(img)

    cx, cy = w // 2, 190
    draw.ellipse([cx - 86, cy - 86, cx + 86, cy + 86], outline=ACCENT, width=6)
    draw.ellipse([cx - 62, cy - 62, cx + 62, cy + 62], outline=ACCENT_DIM, width=3)
    draw.line([cx, cy - 40, cx, cy + 40], fill=ACCENT, width=10)

    _centered(draw, w, 320, "ZAPRET", _font(46), WHITE)
    _centered(draw, w, 378, "L A U N C H E R", _font(20), ACCENT)
    _centered(draw, w, 418, "DPI bypass · Windows", _font(15, bold=False), MUTED)

    badge = "v17.4"
    bf = _font(16)
    bbox = draw.textbbox((0, 0), badge, font=bf)
    bw = bbox[2] - bbox[0] + 28
    draw.rounded_rectangle([cx - bw // 2, 452, cx + bw // 2, 486], radius=16, outline=ACCENT, width=2)
    _centered(draw, w, 458, badge, bf, ACCENT)

    feats = ["YouTube", "Discord", "Telegram", "WebView2 / Tk"]
    y = 528
    for name in feats:
        draw.ellipse([cx - 70, y + 4, cx - 62, y + 12], fill=ACCENT)
        draw.text((cx - 50, y), name, font=_font(15, bold=False), fill=WHITE)
        y += 26

    img.convert("RGB").save(path, "BMP")
    return path


def make_wizard_small(path):
    size = 110
    img = Image.new("RGB", (size, size), BG_TOP)
    img = img.convert("RGBA")
    img = Image.alpha_composite(img, _glow((size, size), (size // 2, size // 2), 46, ACCENT, 110))
    draw = ImageDraw.Draw(img)
    draw.ellipse([16, 16, size - 17, size - 17], outline=ACCENT, width=6)
    draw.line([size // 2, 34, size // 2, size - 34], fill=ACCENT, width=8)
    img.convert("RGB").save(path, "BMP")
    return path


def make_wizard_back(path):
    w, h = 800, 600
    img = Image.new("RGB", (w, h), BG_TOP)
    _vgradient(img, (8, 9, 24), (14, 16, 40))
    img = img.convert("RGBA")
    draw = ImageDraw.Draw(img)
    _grid(draw, w, h, step=34, color=(20, 24, 54))
    img = Image.alpha_composite(img, _glow((w, h), (140, 120), 220, ACCENT, 46))
    img = Image.alpha_composite(img, _glow((w, h), (680, 500), 240, CYAN, 34))
    draw = ImageDraw.Draw(img)
    for i in range(6):
        x = 60 + i * 130
        draw.line([(x, h), (x + 220, 0)], fill=(18, 22, 50), width=2)
    img.convert("RGB").save(path, "BMP")
    return path


FRAME_COUNT = 16
BANNER_W, BANNER_H = 640, 150


def make_anim_frames(out_dir):
    """Кадры анимированного баннера: пульсирующие кольца + орбитальные точки + логотип."""
    os.makedirs(out_dir, exist_ok=True)
    paths = []
    cx, cy = BANNER_W // 2, 54
    for idx in range(FRAME_COUNT):
        t = idx / FRAME_COUNT
        img = Image.new("RGB", (BANNER_W, BANNER_H), BG_TOP)
        _vgradient(img, (8, 9, 24), (16, 19, 46))
        img = img.convert("RGBA")
        img = Image.alpha_composite(img, _glow((BANNER_W, BANNER_H), (cx, cy), 90, ACCENT, 70))
        draw = ImageDraw.Draw(img)
        for i in range(3):
            phase = (t + i / 3.0) % 1.0
            r = 26 + phase * 74
            color = tuple(int(BG_TOP[j] + (ACCENT[j] - BG_TOP[j]) * max(0.0, 1.0 - phase)) for j in range(3))
            draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline=color, width=2)
        r0 = 24 + 4 * math.sin(t * 2 * math.pi)
        draw.ellipse([cx - r0, cy - r0, cx + r0, cy + r0], outline=ACCENT, width=3)
        draw.line([cx, cy - 10, cx, cy + 10], fill=ACCENT, width=4)
        for k in range(6):
            ang = (k / 6.0) * 2 * math.pi + t * 2 * math.pi
            px, py = cx + math.cos(ang) * 46, cy + math.sin(ang) * 46
            draw.ellipse([px - 3, py - 3, px + 3, py + 3], fill=ACCENT_DIM)
        path = os.path.join(out_dir, f"anim_{idx:02d}.bmp")
        img.convert("RGB").save(path, "BMP")
        paths.append(path)
    return paths


def make_ui_images(out_dir):
    """Трек/заливка прогресса и баннер финиша."""
    track = Image.new("RGB", (600, 16), (14, 17, 36))
    d = ImageDraw.Draw(track)
    d.rounded_rectangle([0, 0, 599, 15], radius=8, outline=(42, 48, 94), width=2)
    track.save(os.path.join(out_dir, "progress_track.bmp"), "BMP")

    fill = Image.new("RGB", (600, 16), (8, 9, 24))
    d = ImageDraw.Draw(fill)
    d.rounded_rectangle([0, 0, 599, 15], radius=8, fill=ACCENT)
    fill.save(os.path.join(out_dir, "progress_fill.bmp"), "BMP")

    fin = Image.new("RGB", (BANNER_W, BANNER_H), BG_TOP)
    _vgradient(fin, (8, 9, 24), (16, 19, 46))
    fin = fin.convert("RGBA")
    fin = Image.alpha_composite(fin, _glow((BANNER_W, BANNER_H), (BANNER_W // 2, 54), 90, ACCENT, 80))
    d = ImageDraw.Draw(fin)
    cx, cy = BANNER_W // 2, 54
    d.ellipse([cx - 34, cy - 34, cx + 34, cy + 34], outline=ACCENT, width=5)
    d.line([cx - 16, cy + 2, cx - 4, cy + 14], fill=ACCENT, width=7)
    d.line([cx - 4, cy + 14, cx + 18, cy - 12], fill=ACCENT, width=7)
    fin.convert("RGB").save(os.path.join(out_dir, "finish_banner.bmp"), "BMP")
    return True


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    print("OK:", make_wizard_image(os.path.join(OUT_DIR, "wizard_image.bmp")))
    print("OK:", make_wizard_small(os.path.join(OUT_DIR, "wizard_small.bmp")))
    print("OK:", make_wizard_back(os.path.join(OUT_DIR, "wizard_back.bmp")))
    frames = make_anim_frames(os.path.join(OUT_DIR, "frames"))
    print(f"OK: {len(frames)} animation frames -> installer/frames/")
    make_ui_images(OUT_DIR)
    print("OK: progress_track/fill + finish_banner")
    return 0


if __name__ == "__main__":
    sys.exit(main())
