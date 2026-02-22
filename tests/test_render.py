"""Tests for weather image rendering.

These tests verify the rendered image has the correct dimensions,
mode, and contains visible content -- the properties that matter
for the QGIF encoder and keyboard display.
"""

from datetime import datetime

import pytest
from PIL import Image

from rt82weather.providers import IconType, WeatherForecast
from rt82weather.render import (
    render_weather, DISPLAY_WIDTH, DISPLAY_HEIGHT,
)


@pytest.fixture
def sample_forecast():
    return WeatherForecast(
        condition="sunny",
        temp_min_c=5.0,
        temp_max_c=22.0,
        icon_type=IconType.SUN,
        location_name="Test City",
    )


class TestDisplayDimensions:
    def test_width_is_240(self):
        assert DISPLAY_WIDTH == 240

    def test_height_is_136(self):
        """Height must be 136 (divisible by 4) for the native QGIF encoder."""
        assert DISPLAY_HEIGHT == 136

    def test_height_divisible_by_4(self):
        assert DISPLAY_HEIGHT % 4 == 0


class TestRenderWeather:
    def test_output_dimensions(self, sample_forecast):
        img = render_weather(sample_forecast)
        assert img.size == (DISPLAY_WIDTH, DISPLAY_HEIGHT)
        assert img.size == (240, 136)

    def test_output_mode_rgb(self, sample_forecast):
        img = render_weather(sample_forecast)
        assert img.mode == "RGB"

    def test_not_blank(self, sample_forecast):
        """The image should contain more than just the background color."""
        img = render_weather(sample_forecast)
        colors = img.getcolors(maxcolors=50000)
        bg_color = (10, 10, 15)
        non_bg = [c for c in colors if c[1] != bg_color]
        assert len(non_bg) > 10, "Rendered image appears blank"

    def test_deterministic_with_fixed_time(self, sample_forecast):
        t = datetime(2026, 6, 15, 14, 30, 0)
        img1 = render_weather(sample_forecast, now=t)
        img2 = render_weather(sample_forecast, now=t)
        get1 = getattr(img1, "get_flattened_data", img1.getdata)
        get2 = getattr(img2, "get_flattened_data", img2.getdata)
        assert list(get1()) == list(get2())

    @pytest.mark.parametrize("icon_type", list(IconType))
    def test_all_icon_types_render(self, icon_type):
        forecast = WeatherForecast(
            condition="test",
            temp_min_c=-10.0,
            temp_max_c=40.0,
            icon_type=icon_type,
        )
        img = render_weather(forecast)
        assert img.size == (240, 136)

    def test_negative_temperatures(self):
        forecast = WeatherForecast(
            condition="snow",
            temp_min_c=-15.0,
            temp_max_c=-2.0,
            icon_type=IconType.SNOW,
        )
        img = render_weather(forecast)
        assert img.size == (240, 136)

    def test_accepts_now_parameter(self, sample_forecast):
        t = datetime(2026, 12, 25, 8, 0, 0)
        img = render_weather(sample_forecast, now=t)
        assert img.size == (240, 136)
