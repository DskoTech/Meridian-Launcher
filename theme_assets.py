"""
theme_assets.py — renders the default placeholder background and overlay
PNGs for each theme, for both Meridian Launcher and Meridian Game Library.

Each theme gets its own look, and Launcher vs Game Library get distinct
variants of each (different accent + label) so it's obvious which app a
stray file belongs to. Everything is generated programmatically with
Pillow into the app-data assets folder and only rebuilt when missing, so
first run is self-healing and nothing needs to ship as a binary.

Public API:
    ensure_theme_assets(assets_dir, app="launcher"|"library")
    placeholder_background(assets_dir, app, layout) -> path
    placeholder_overlay(assets_dir, app, layout) -> path
"""

import math
import os

try:
    from PIL import Image, ImageDraw
    _HAVE_PIL = True
except ImportError:
    _HAVE_PIL = False

W, H = 1920, 1080

# per-theme base + accent colors (RGB)
THEMES = {
    "dawning_horizon": {"top": (24, 32, 54), "bottom": (12, 16, 30), "accent": (120, 180, 255)},
    "night_horizon": {"top": (10, 12, 20), "bottom": (4, 5, 10), "accent": (90, 120, 200)},
    "cyber_radial": {"top": (18, 8, 30), "bottom": (6, 4, 14), "accent": (255, 90, 200)},
}

# app tint so Launcher vs Library variants are visibly different
APP_TINT = {
    "launcher": (0, 40, 60),
    "library": (50, 20, 60),
}


def _key(app, layout, kind):
    return f"{kind}_{app}_{layout}.png"


def _vgrad(top, bottom):
    img = Image.new("RGB", (W, H))
    px = img.load()
    for y in range(H):
        t = y / (H - 1)
        r = int(top[0] * (1 - t) + bottom[0] * t)
        g = int(top[1] * (1 - t) + bottom[1] * t)
        b = int(top[2] * (1 - t) + bottom[2] * t)
        for x in range(W):
            px[x, y] = (r, g, b)
    return img


def _render_background(app, layout):
    theme = THEMES.get(layout, THEMES["dawning_horizon"])
    tint = APP_TINT.get(app, (0, 0, 0))
    top = tuple(min(255, c + t // 3) for c, t in zip(theme["top"], tint))
    img = _vgrad(top, theme["bottom"])
    draw = ImageDraw.Draw(img, "RGBA")
    accent = theme["accent"]

    # a faint grid + a soft accent glow, distinct per theme
    step = 120
    for x in range(0, W, step):
        draw.line([(x, 0), (x, H)], fill=(accent[0], accent[1], accent[2], 16), width=1)
    for y in range(0, H, step):
        draw.line([(0, y), (W, y)], fill=(accent[0], accent[1], accent[2], 16), width=1)

    if layout == "cyber_radial":
        cx, cy = W // 2, H // 2
        for r in range(120, 900, 120):
            draw.ellipse([cx - r, cy - r, cx + r, cy + r],
                         outline=(accent[0], accent[1], accent[2], 26), width=2)
    else:
        # dawning/night: a low horizon glow band
        band_y = int(H * 0.62)
        for i in range(120):
            a = int(40 * (1 - i / 120))
            draw.line([(0, band_y + i), (W, band_y + i)],
                      fill=(accent[0], accent[1], accent[2], a), width=1)
    return img


def _render_overlay(app, layout):
    """A transparent frame overlay: white pixels become see-through in the
    app (its overlay canvas keys out near-white), so the *non*-white parts
    are what actually show. We draw the frame in near-white so the app's
    keying leaves a clean thin vignette + corner brackets tinted by theme."""
    theme = THEMES.get(layout, THEMES["dawning_horizon"])
    accent = theme["accent"]
    img = Image.new("RGBA", (W, H), (255, 255, 255, 0))
    draw = ImageDraw.Draw(img)
    m = 26
    # corner brackets in theme accent (kept dark enough to survive keying)
    L = 160
    col = (accent[0] // 2, accent[1] // 2, accent[2] // 2, 255)
    for (cx, cy, dx, dy) in [(m, m, 1, 1), (W - m, m, -1, 1),
                             (m, H - m, 1, -1), (W - m, H - m, -1, -1)]:
        draw.line([(cx, cy), (cx + dx * L, cy)], fill=col, width=6)
        draw.line([(cx, cy), (cx, cy + dy * L)], fill=col, width=6)
    return img


def _ensure(path, render_fn):
    if os.path.exists(path):
        return path
    if not _HAVE_PIL:
        return None
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        render_fn().save(path, "PNG")
    except Exception:
        return None
    return path


def placeholder_background(assets_dir, app, layout):
    path = os.path.join(assets_dir, _key(app, layout, "bg"))
    return _ensure(path, lambda: _render_background(app, layout))


def placeholder_overlay(assets_dir, app, layout):
    path = os.path.join(assets_dir, _key(app, layout, "overlay"))
    return _ensure(path, lambda: _render_overlay(app, layout))


def ensure_theme_assets(assets_dir, app="launcher"):
    """Render every theme's background + overlay placeholder for this app if
    any are missing. Cheap after first run (all files exist)."""
    out = {}
    for layout in THEMES:
        out[layout] = {
            "background": placeholder_background(assets_dir, app, layout),
            "overlay": placeholder_overlay(assets_dir, app, layout),
        }
    return out
