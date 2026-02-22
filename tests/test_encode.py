"""Tests for QGIF encoding fallback logic."""

from pathlib import Path
from unittest.mock import patch

import pytest
from PIL import Image

from rt82weather.cli import _encode_weather_image
from rt82weather.render import DISPLAY_WIDTH, DISPLAY_HEIGHT


@pytest.fixture
def sample_image():
    return Image.new("RGB", (DISPLAY_WIDTH, DISPLAY_HEIGHT), (10, 10, 15))


class TestEncodeWeatherImage:
    def test_python_fallback_produces_valid_qgif(self, sample_image, tmp_path):
        """When native encoder is missing, Python encoder produces valid QGIF."""
        qgif_path = tmp_path / "test.qgif"
        with patch("rt82display.cli.encode_frames_to_qgif", side_effect=FileNotFoundError):
            data = _encode_weather_image(sample_image, qgif_path)

        assert data[:4] == bytearray(b"QGIF")
        assert len(data) > 32

    def test_python_fallback_uses_correct_dimensions(self, sample_image, tmp_path):
        """Python fallback must encode at 240x136, not the default 240x135."""
        qgif_path = tmp_path / "test.qgif"
        with patch("rt82display.cli.encode_frames_to_qgif", side_effect=FileNotFoundError):
            data = _encode_weather_image(sample_image, qgif_path)

        import struct
        width = struct.unpack_from("<H", data, 6)[0]
        height = struct.unpack_from("<H", data, 8)[0]
        assert width == 240
        assert height == 136
