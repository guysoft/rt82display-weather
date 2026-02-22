"""Render weather data to a 240x136 image for the RT82 display.

Layout:
  [date  time]
  [icon] min/max°C
         condition

The native QGIF encoder requires dimensions divisible by 4, so the
display height is 136 (not 135). The extra row is imperceptible.
"""

from datetime import datetime
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from .providers import WeatherForecast
from .icons import draw_icon

DISPLAY_WIDTH = 240
DISPLAY_HEIGHT = 136

_BG_COLOR = (10, 10, 15)
_TEXT_COLOR = (240, 240, 240)
_TEMP_MIN_COLOR = (100, 180, 255)
_TEMP_MAX_COLOR = (255, 120, 80)
_LABEL_COLOR = (160, 160, 170)
_DATE_COLOR = (130, 130, 140)

_HEADER_HEIGHT = 18
ICON_SIZE = 72
ICON_X = 10
ICON_Y = _HEADER_HEIGHT + (DISPLAY_HEIGHT - _HEADER_HEIGHT - ICON_SIZE) // 2


def _load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        "/System/Library/Fonts/SFCompact.ttf",
    ]
    for path in candidates:
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def render_weather(forecast: WeatherForecast, now: datetime | None = None) -> Image.Image:
    """Render a weather forecast to a 240x136 RGB image."""
    if now is None:
        now = datetime.now()

    img = Image.new("RGB", (DISPLAY_WIDTH, DISPLAY_HEIGHT), _BG_COLOR)
    draw = ImageDraw.Draw(img)

    # -- Date & time header --
    font_date = _load_font(12)
    date_str = now.strftime("%b %d")
    hour = now.hour % 12 or 12
    ampm = "AM" if now.hour < 12 else "PM"
    time_str = f"{hour}{ampm}"

    draw.text((6, 3), date_str, fill=_DATE_COLOR, font=font_date)

    time_bbox = draw.textbbox((0, 0), time_str, font=font_date)
    time_w = time_bbox[2] - time_bbox[0]
    draw.text((DISPLAY_WIDTH - time_w - 6, 3), time_str, fill=_DATE_COLOR, font=font_date)

    # -- Weather icon --
    icon_img = draw_icon(forecast.icon_type, ICON_SIZE)
    img.paste(icon_img, (ICON_X, ICON_Y), icon_img)

    # -- Temperature --
    text_x = ICON_X + ICON_SIZE + 12
    text_area_w = DISPLAY_WIDTH - text_x - 8

    font_temp = _load_font(34)
    font_label = _load_font(15)

    min_t = f"{forecast.temp_min_c:.0f}"
    max_t = f"{forecast.temp_max_c:.0f}"

    content_top = _HEADER_HEIGHT
    content_h = DISPLAY_HEIGHT - content_top
    temp_y = content_top + content_h // 2 - 22

    min_bbox = draw.textbbox((0, 0), min_t, font=font_temp)
    min_w = min_bbox[2] - min_bbox[0]

    slash_bbox = draw.textbbox((0, 0), "/", font=font_temp)
    slash_w = slash_bbox[2] - slash_bbox[0]

    max_bbox = draw.textbbox((0, 0), max_t, font=font_temp)
    max_w = max_bbox[2] - max_bbox[0]

    deg_bbox = draw.textbbox((0, 0), "°C", font=font_label)
    deg_w = deg_bbox[2] - deg_bbox[0]

    total_w = min_w + slash_w + max_w + 4 + deg_w
    start_x = text_x + (text_area_w - total_w) // 2

    x = start_x
    draw.text((x, temp_y), min_t, fill=_TEMP_MIN_COLOR, font=font_temp)
    x += min_w

    draw.text((x, temp_y), "/", fill=_LABEL_COLOR, font=font_temp)
    x += slash_w

    draw.text((x, temp_y), max_t, fill=_TEMP_MAX_COLOR, font=font_temp)
    x += max_w + 2

    draw.text((x, temp_y + 4), "°C", fill=_LABEL_COLOR, font=font_label)

    # -- Condition text --
    condition_font = _load_font(13)
    condition_text = forecast.condition.capitalize()
    cond_bbox = draw.textbbox((0, 0), condition_text, font=condition_font)
    cond_w = cond_bbox[2] - cond_bbox[0]
    cond_x = text_x + (text_area_w - cond_w) // 2
    cond_y = temp_y + 42
    draw.text((cond_x, cond_y), condition_text, fill=_LABEL_COLOR, font=condition_font)

    return img
