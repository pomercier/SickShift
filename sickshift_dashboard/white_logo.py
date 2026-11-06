"""
Network logo analyzer and white silhouette transformer with transparent background.
Forces clean, sharp, pure white monochrome logos with transparent backgrounds.
Normalizes all logos onto a standardized canvas so they share the exact same width and similar height.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional, Tuple

try:
    from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageStat
except ImportError:
    Image = None  # type: ignore
    ImageDraw = None  # type: ignore
    ImageFilter = None  # type: ignore
    ImageFont = None  # type: ignore
    ImageStat = None  # type: ignore


CACHE_SUBDIR = ".white_cache"
CANVAS_WIDTH = 200
CANVAS_HEIGHT = 60
CONTENT_MAX_WIDTH = 170
CONTENT_MAX_HEIGHT = 46


def extract_white_foreground(orig: Image.Image) -> Image.Image:
    """Extracts foreground elements as pure white on transparent background."""
    im = orig.convert("RGBA")
    w, h = im.size

    alpha = im.split()[3]
    alpha_pixels = list(alpha.getdata()) if hasattr(alpha, "getdata") else list(alpha.getchannel(0).getdata())
    opaque_ratio = sum(1 for p in alpha_pixels if p > 35) / max(1, w * h)

    # 1. Native transparent background: convert visible pixels to pure white
    if opaque_ratio < 0.85:
        r, g, b, a = im.split()
        white_solid = Image.new("L", (w, h), 255)
        return Image.merge("RGBA", (white_solid, white_solid, white_solid, a))

    # 2. Opaque or solid/gradient background: extract light/white foreground
    corners = [
        im.getpixel((0, 0)),
        im.getpixel((w - 1, 0)),
        im.getpixel((0, h - 1)),
        im.getpixel((w - 1, h - 1)),
    ]
    bg_lum = sum(0.299 * c[0] + 0.587 * c[1] + 0.114 * c[2] for c in corners) / 4.0

    new_data = []
    for p in im.getdata():
        lum = 0.299 * p[0] + 0.587 * p[1] + 0.114 * p[2]
        sat = max(p[:3]) - min(p[:3])
        if bg_lum < 160:
            # Dark or colored background (e.g. Prime Video blue, Tou.tv teal, Disney+ navy)
            if lum > bg_lum + 30 and sat < 120:
                alpha_val = min(255, int(((lum - bg_lum - 20) / 35.0) * 255))
                new_data.append((255, 255, 255, alpha_val))
            else:
                new_data.append((255, 255, 255, 0))
        else:
            # Light background: dark foreground
            if lum < bg_lum - 35:
                alpha_val = min(255, int(((bg_lum - lum - 25) / 35.0) * 255))
                new_data.append((255, 255, 255, alpha_val))
            else:
                new_data.append((255, 255, 255, 0))

    result = Image.new("RGBA", (w, h))
    result.putdata(new_data)
    return result


def compose_horizontal_lockup(cropped: Image.Image, name_hint: str) -> Image.Image:
    """Builds a horizontal lockup for square/tall icons to achieve uniform width."""
    name_clean = name_hint.lower().replace("-", " ").replace("_", " ").strip()
    if "comedy" in name_clean:
        # Scale the Comedy Central mark to fit on left and add clean COMEDY CENTRAL text
        target_h = 42
        scale = target_h / max(1, cropped.height)
        icon_w = int(cropped.width * scale)
        resample = getattr(Image, "Resampling", Image).LANCZOS
        icon = cropped.resize((icon_w, target_h), resample)

        comp = Image.new("RGBA", (175, target_h), (0, 0, 0, 0))
        comp.paste(icon, (0, 0), icon)

        draw = ImageDraw.Draw(comp)
        text_x = icon_w + 10
        draw.text((text_x, 4), "COMEDY", fill=(255, 255, 255, 255))
        draw.text((text_x, 22), "CENTRAL", fill=(255, 255, 255, 255))
        return comp

    return cropped


def standardize_to_canvas(cropped: Image.Image, name_hint: str = "") -> Image.Image:
    """Normalizes cropped logo onto a standardized 200x60 canvas with optically uniform visual weight."""
    cw, ch = cropped.size
    if cw <= 0 or ch <= 0:
        return Image.new("RGBA", (CANVAS_WIDTH, CANVAS_HEIGHT), (0, 0, 0, 0))

    aspect = cw / float(ch)
    if aspect < 1.7:
        cropped = compose_horizontal_lockup(cropped, name_hint)
        cw, ch = cropped.size
        aspect = cw / float(ch)

    # Optically balanced height target on 200x60 canvas
    if aspect >= 5.2:
        target_h = 36.0
    elif aspect >= 4.2:
        target_h = 40.0
    elif aspect >= 3.4:
        target_h = 44.0
    elif aspect >= 2.8:
        target_h = 48.0
    elif aspect >= 2.0:
        target_h = 51.0
    else:
        target_h = 52.0

    target_w = target_h * aspect
    max_w = 188.0
    max_h = 52.0
    if target_w > max_w:
        scale = max_w / target_w
        target_w = max_w
        target_h = target_h * scale
    if target_h > max_h:
        scale = max_h / target_h
        target_h = max_h
        target_w = target_w * scale

    new_w = max(1, int(round(target_w)))
    new_h = max(1, int(round(target_h)))

    resample = getattr(Image, "Resampling", Image).LANCZOS
    resized = cropped.resize((new_w, new_h), resample)

    canvas = Image.new("RGBA", (CANVAS_WIDTH, CANVAS_HEIGHT), (0, 0, 0, 0))
    paste_x = (CANVAS_WIDTH - new_w) // 2
    paste_y = (CANVAS_HEIGHT - new_h) // 2
    canvas.paste(resized, (paste_x, paste_y), resized)
    return canvas


def transform_to_white_monochrome(im_path: Path) -> Tuple[bool, Optional[Image.Image], str]:
    """Transforms network logo into standardized white silhouette on transparent background."""
    if Image is None:
        return False, None, "Pillow not installed"

    try:
        orig = Image.open(im_path).convert("RGBA")
    except Exception as exc:
        return False, None, f"Open error: {exc}"

    white_raw = extract_white_foreground(orig)
    bbox = white_raw.split()[3].getbbox()

    if not bbox:
        # If extraction found nothing, create clean text badge
        stem_name = im_path.stem
        canvas = Image.new("RGBA", (CANVAS_WIDTH, CANVAS_HEIGHT), (0, 0, 0, 0))
        draw = ImageDraw.Draw(canvas)
        draw.text((15, 20), stem_name.upper(), fill=(255, 255, 255, 255))
        return True, canvas, "Synthesized fallback"

    cropped = white_raw.crop(bbox)
    standardized = standardize_to_canvas(cropped, name_hint=im_path.stem)
    return True, standardized, "Standardized white logo"


def get_white_or_original_logo(logo_path: Path, cache_dir: Optional[Path] = None) -> Path:
    """Returns path to cached standardized white logo on transparent background."""
    if not logo_path.exists():
        return logo_path

    if Image is None:
        return logo_path

    if cache_dir is None:
        cache_dir = logo_path.parent / CACHE_SUBDIR

    try:
        cache_dir.mkdir(parents=True, exist_ok=True)
    except Exception:
        return logo_path

    cached_white = cache_dir / logo_path.name

    # Verify existing cache (with mtime invalidation)
    try:
        src_mtime = logo_path.stat().st_mtime
        if cached_white.exists() and cached_white.stat().st_mtime >= src_mtime:
            return cached_white
    except Exception:
        pass

    ok, white_im, _reason = transform_to_white_monochrome(logo_path)
    if ok and white_im is not None:
        try:
            white_im.save(cached_white, format="PNG", optimize=True)
            return cached_white
        except Exception:
            pass

    return logo_path
