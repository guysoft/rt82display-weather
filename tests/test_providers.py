"""Tests for the provider interface and BBC Weather provider."""

from unittest.mock import patch, MagicMock

import pytest

from rt82weather.providers import (
    IconType, Location, WeatherForecast, WeatherProvider,
    register_provider, get_provider, list_providers,
)
from rt82weather.providers.bbc import BBCWeatherProvider, _condition_to_icon


class TestProviderRegistry:
    def test_bbc_registered(self):
        assert "bbc" in list_providers()

    def test_get_bbc(self):
        prov = get_provider("bbc")
        assert isinstance(prov, BBCWeatherProvider)

    def test_get_unknown_raises(self):
        with pytest.raises(ValueError, match="Unknown provider"):
            get_provider("nonexistent")

    def test_verify_ssl_propagated(self):
        prov = get_provider("bbc", verify_ssl=False)
        assert prov.verify_ssl is False

        prov2 = get_provider("bbc", verify_ssl=True)
        assert prov2.verify_ssl is True


class TestConditionMapping:
    @pytest.mark.parametrize("condition,expected", [
        ("sunny", IconType.SUN),
        ("clear sky", IconType.SUN),
        ("Sunny Intervals", IconType.PARTLY_CLOUDY),
        ("light cloud", IconType.PARTLY_CLOUDY),
        ("cloudy", IconType.CLOUD),
        ("thick cloud", IconType.CLOUD),
        ("heavy rain", IconType.RAIN),
        ("light shower", IconType.RAIN),
        ("thunderstorm", IconType.THUNDERSTORM),
        ("thundery showers", IconType.THUNDERSTORM),
        ("light snow", IconType.SNOW),
        ("heavy snow shower", IconType.SNOW),
        ("mist", IconType.MIST),
        ("fog", IconType.MIST),
        ("hazy", IconType.MIST),
        ("sleet", IconType.RAIN),
    ])
    def test_known_conditions(self, condition, expected):
        assert _condition_to_icon(condition) == expected

    def test_unknown_defaults_to_cloud(self):
        assert _condition_to_icon("alien weather") == IconType.CLOUD

    def test_case_insensitive(self):
        assert _condition_to_icon("SUNNY") == IconType.SUN
        assert _condition_to_icon("  sunny  ") == IconType.SUN


_SEARCH_RESPONSE = {
    "response": {
        "locations": [
            {"id": "123", "name": "London", "container": "Greater London",
             "country": "GB", "placeType": "settlement"},
            {"id": "456", "name": "London", "container": "Canada",
             "country": "CA", "placeType": "settlement"},
            {"id": "789", "name": "London Region", "container": "England",
             "country": "GB", "placeType": "region"},
        ]
    }
}

_FORECAST_RESPONSE = {
    "forecasts": [{
        "summary": {
            "report": {
                "weatherTypeText": "Sunny",
                "minTempC": 5,
                "maxTempC": 18,
                "humidityPercent": 60,
                "windSpeedKph": 15,
            }
        }
    }]
}


class TestBBCSearchLocation:
    @patch("rt82weather.providers.bbc.requests.get")
    def test_search_returns_locations(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.json.return_value = _SEARCH_RESPONSE
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        prov = BBCWeatherProvider()
        results = prov.search_location("London")

        assert len(results) == 2  # region filtered out
        assert results[0].id == "123"
        assert results[0].name == "London"
        assert results[1].id == "456"

    @patch("rt82weather.providers.bbc.requests.get")
    def test_search_deduplicates(self, mock_get):
        duped = {
            "response": {
                "locations": [
                    {"id": "1", "name": "A", "container": "B", "country": "C"},
                    {"id": "1", "name": "A", "container": "B", "country": "C"},
                ]
            }
        }
        mock_resp = MagicMock()
        mock_resp.json.return_value = duped
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        results = BBCWeatherProvider().search_location("test")
        assert len(results) == 1

    @patch("rt82weather.providers.bbc.requests.get")
    def test_search_passes_verify(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"response": {"locations": []}}
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        prov = BBCWeatherProvider()
        prov.verify_ssl = False
        prov.search_location("test")

        _, kwargs = mock_get.call_args
        assert kwargs["verify"] is False


class TestBBCForecast:
    @patch("rt82weather.providers.bbc.requests.get")
    def test_forecast_parses(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.json.return_value = _FORECAST_RESPONSE
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        forecast = BBCWeatherProvider().get_forecast("123")

        assert forecast.condition == "sunny"
        assert forecast.temp_min_c == 5.0
        assert forecast.temp_max_c == 18.0
        assert forecast.icon_type == IconType.SUN
        assert forecast.humidity == 60
        assert forecast.wind_speed_kph == 15

    @patch("rt82weather.providers.bbc.requests.get")
    def test_forecast_missing_temps_raises(self, mock_get):
        bad_resp = {"forecasts": [{"summary": {"report": {"weatherTypeText": "Sunny"}}}]}
        mock_resp = MagicMock()
        mock_resp.json.return_value = bad_resp
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        with pytest.raises(ValueError, match="missing temperature"):
            BBCWeatherProvider().get_forecast("123")

    @patch("rt82weather.providers.bbc.requests.get")
    def test_forecast_empty_raises(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"forecasts": []}
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        with pytest.raises(ValueError, match="No forecast data"):
            BBCWeatherProvider().get_forecast("123")

    @patch("rt82weather.providers.bbc.requests.get")
    def test_forecast_passes_verify(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.json.return_value = _FORECAST_RESPONSE
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        prov = BBCWeatherProvider()
        prov.verify_ssl = False
        prov.get_forecast("123")

        _, kwargs = mock_get.call_args
        assert kwargs["verify"] is False
