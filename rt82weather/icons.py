"""Programmatic weather icon drawing with Pillow.

Each icon is drawn at a given size on a transparent RGBA canvas.
Designed to be readable on the RT82's 240x135 display.
"""

import math
from PIL import Image, ImageDraw

from .providers import IconType

# Icon palette (bright on dark background)
_SUN_YELLOW = (255, 210, 50)
_CLOUD_WHITE = (220, 220, 230)
_CLOUD_GREY = (160, 165, 175)
_RAIN_BLUE = (80, 170, 255)
_SNOW_WHITE = (230, 235, 255)
_BOLT_YELLOW = (255, 240, 80)
_MIST_GREY = (180, 185, 195)


def _draw_sun(draw: ImageDraw.ImageDraw, cx: int, cy: int, r: int) -> None:
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=_SUN_YELLOW)
    ray_len = r * 0.55
    for angle_deg in range(0, 360, 45):
        a = math.radians(angle_deg)
        x1 = cx + math.cos(a) * (r + 3)
        y1 = cy + math.sin(a) * (r + 3)
        x2 = cx + math.cos(a) * (r + 3 + ray_len)
        y2 = cy + math.sin(a) * (r + 3 + ray_len)
        draw.line([(x1, y1), (x2, y2)], fill=_SUN_YELLOW, width=max(2, r // 6))


def _draw_cloud(draw: ImageDraw.ImageDraw, cx: int, cy: int, w: int, h: int,
                color: tuple = _CLOUD_WHITE) -> None:
    ew = w * 0.45
    eh = h * 0.55
    draw.ellipse([cx - w * 0.35, cy - h * 0.15, cx - w * 0.35 + ew, cy - h * 0.15 + eh], fill=color)
    draw.ellipse([cx - w * 0.1, cy - h * 0.45, cx - w * 0.1 + ew * 1.1, cy - h * 0.45 + eh * 1.1], fill=color)
    draw.ellipse([cx + w * 0.05, cy - h * 0.2, cx + w * 0.05 + ew, cy - h * 0.2 + eh], fill=color)
    draw.rectangle([cx - w * 0.35, cy + h * 0.05, cx + w * 0.45, cy + h * 0.25], fill=color)


def _draw_rain_drops(draw: ImageDraw.ImageDraw, cx: int, cy: int, w: int, count: int = 3) -> None:
    spacing = w // (count + 1)
    start_x = cx - w // 2 + spacing
    for i in range(count):
        x = start_x + i * spacing
        draw.line([(x, cy), (x - 3, cy + 10)], fill=_RAIN_BLUE, width=2)


def _draw_snow_dots(draw: ImageDraw.ImageDraw, cx: int, cy: int, w: int, count: int = 4) -> None:
    spacing = w // (count + 1)
    start_x = cx - w // 2 + spacing
    for i in range(count):
        x = start_x + i * spacing
        y = cy + (i % 2) * 5
        r = 2
        draw.ellipse([x - r, y - r, x + r, y + r], fill=_SNOW_WHITE)


def _draw_bolt(draw: ImageDraw.ImageDraw, cx: int, cy: int) -> None:
    points = [
        (cx - 2, cy), (cx - 6, cy + 10), (cx - 1, cy + 8),
        (cx + 2, cy + 18), (cx + 4, cy + 8), (cx + 1, cy + 10),
    ]
    draw.polygon(points, fill=_BOLT_YELLOW)


def draw_icon(icon_type: IconType, size: int = 80) -> Image.Image:
    """Draw a weather icon on a transparent RGBA canvas."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    cx, cy = size // 2, size // 2
    r = size // 4

    if icon_type == IconType.SUN:
        _draw_sun(draw, cx, cy, r)

    elif icon_type == IconType.PARTLY_CLOUDY:
        _draw_sun(draw, cx - size // 8, cy - size // 8, r * 0.7)
        _draw_cloud(draw, cx + size // 10, cy + size // 10, size * 0.5, size * 0.35)

    elif icon_type == IconType.CLOUD:
        _draw_cloud(draw, cx, cy - size // 12, size * 0.6, size * 0.4, _CLOUD_GREY)

    elif icon_type == IconType.RAIN:
        _draw_cloud(draw, cx, cy - size // 6, size * 0.55, size * 0.35, _CLOUD_GREY)
        _draw_rain_drops(draw, cx, cy + size // 6, int(size * 0.5), 4)

    elif icon_type == IconType.SNOW:
        _draw_cloud(draw, cx, cy - size // 6, size * 0.55, size * 0.35, _CLOUD_WHITE)
        _draw_snow_dots(draw, cx, cy + size // 6, int(size * 0.5), 5)

    elif icon_type == IconType.THUNDERSTORM:
        _draw_cloud(draw, cx, cy - size // 5, size * 0.6, size * 0.38, _CLOUD_GREY)
        _draw_bolt(draw, cx, cy + size // 8)

    elif icon_type == IconType.MIST:
        y_start = cy - size // 6
        for i in range(4):
            y = y_start + i * (size // 8)
            half_w = size // 3 - abs(i - 1.5) * 4
            draw.line([(cx - half_w, y), (cx + half_w, y)], fill=_MIST_GREY, width=3)

    return img
