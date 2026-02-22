"""Tests for weather icon rendering."""

import pytest
from PIL import Image

from rt82weather.icons import draw_icon
from rt82weather.providers import IconType


class TestDrawIcon:
    @pytest.mark.parametrize("icon_type", list(IconType))
    def test_all_icons_produce_rgba_image(self, icon_type):
        img = draw_icon(icon_type, size=80)
        assert isinstance(img, Image.Image)
        assert img.mode == "RGBA"
        assert img.size == (80, 80)

    @pytest.mark.parametrize("icon_type", list(IconType))
    def test_all_icons_have_visible_pixels(self, icon_type):
        """Every icon should draw something (not be fully transparent)."""
        img = draw_icon(icon_type, size=80)
        alpha = img.split()[3]
        get_pixels = getattr(alpha, "get_flattened_data", alpha.getdata)
        non_transparent = sum(1 for p in get_pixels() if p > 0)
        assert non_transparent > 0, f"{icon_type.value} icon is fully transparent"

    def test_custom_size(self):
        img = draw_icon(IconType.SUN, size=120)
        assert img.size == (120, 120)

    def test_small_size(self):
        img = draw_icon(IconType.CLOUD, size=16)
        assert img.size == (16, 16)
