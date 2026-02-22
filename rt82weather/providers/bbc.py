"""BBC Weather provider.

Uses the same undocumented BBC/UK Met Office APIs as KDE Plasma's
weather widget (bbcukmet ion). No API key required.

Endpoints:
  - Location search: open.live.bbc.co.uk/locator/locations
  - Observation:     weather-broker-cdn.api.bbci.co.uk/en/observation/{id}
  - Forecast:        weather-broker-cdn.api.bbci.co.uk/en/forecast/aggregated/{id}
"""

import requests

from . import (
    WeatherProvider, WeatherForecast, Location, IconType,
    register_provider,
)

_SEARCH_URL = "https://open.live.bbc.co.uk/locator/locations"
_OBSERVATION_URL = "https://weather-broker-cdn.api.bbci.co.uk/en/observation/{place_id}"
_FORECAST_URL = "https://weather-broker-cdn.api.bbci.co.uk/en/forecast/aggregated/{place_id}"

_CONDITION_TO_ICON: dict[str, IconType] = {
    "sunny": IconType.SUN,
    "clear": IconType.SUN,
    "clear sky": IconType.SUN,
    "sunny intervals": IconType.PARTLY_CLOUDY,
    "light cloud": IconType.PARTLY_CLOUDY,
    "partly cloudy": IconType.PARTLY_CLOUDY,
    "cloudy": IconType.CLOUD,
    "white cloud": IconType.CLOUD,
    "grey cloud": IconType.CLOUD,
    "thick cloud": IconType.CLOUD,
    "drizzle": IconType.RAIN,
    "light shower": IconType.RAIN,
    "light rain shower": IconType.RAIN,
    "light rain showers": IconType.RAIN,
    "light showers": IconType.RAIN,
    "light rain": IconType.RAIN,
    "heavy rain": IconType.RAIN,
    "heavy showers": IconType.RAIN,
    "heavy shower": IconType.RAIN,
    "heavy rain shower": IconType.RAIN,
    "heavy rain showers": IconType.RAIN,
    "thundery shower": IconType.THUNDERSTORM,
    "thundery showers": IconType.THUNDERSTORM,
    "thunderstorm": IconType.THUNDERSTORM,
    "tropical storm": IconType.THUNDERSTORM,
    "misty": IconType.MIST,
    "mist": IconType.MIST,
    "fog": IconType.MIST,
    "foggy": IconType.MIST,
    "hazy": IconType.MIST,
    "light snow": IconType.SNOW,
    "light snow shower": IconType.SNOW,
    "light snow showers": IconType.SNOW,
    "cloudy with light snow": IconType.SNOW,
    "heavy snow": IconType.SNOW,
    "heavy snow shower": IconType.SNOW,
    "heavy snow showers": IconType.SNOW,
    "cloudy with heavy snow": IconType.SNOW,
    "sleet": IconType.RAIN,
    "sleet shower": IconType.RAIN,
    "sleet showers": IconType.RAIN,
    "cloudy with sleet": IconType.RAIN,
    "hail": IconType.RAIN,
    "hail shower": IconType.RAIN,
    "hail showers": IconType.RAIN,
    "cloudy with hail": IconType.RAIN,
}


def _condition_to_icon(condition: str) -> IconType:
    return _CONDITION_TO_ICON.get(condition.lower().strip(), IconType.CLOUD)


class BBCWeatherProvider(WeatherProvider):
    name = "bbc"

    def search_location(self, query: str) -> list[Location]:
        resp = requests.get(
            _SEARCH_URL,
            params={"s": query, "format": "json"},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()

        locations_raw = (
            data.get("response", {}).get("locations")
            or data.get("response", {}).get("results", {}).get("results")
            or []
        )

        seen_ids: set[str] = set()
        locations: list[Location] = []
        for loc in locations_raw:
            loc_id = loc.get("id", "")
            name = loc.get("name", "")
            area = loc.get("container", "")
            country = loc.get("country", "")
            place_type = loc.get("placeType", "")

            if not loc_id or not name or not area or not country:
                continue
            if place_type == "region":
                continue
            if loc_id in seen_ids:
                continue
            seen_ids.add(loc_id)

            locations.append(Location(
                id=loc_id, name=name, area=area, country=country,
            ))

        return locations

    def get_forecast(self, location_id: str) -> WeatherForecast:
        resp = requests.get(
            _FORECAST_URL.format(place_id=location_id),
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()

        forecasts = data.get("forecasts", [])
        if not forecasts:
            raise ValueError("No forecast data returned")

        today = forecasts[0]
        report = today.get("summary", {}).get("report", {})

        condition = report.get("weatherTypeText", "cloudy").lower()
        temp_min = report.get("minTempC")
        temp_max = report.get("maxTempC")

        if temp_min is None or temp_max is None:
            raise ValueError("Forecast missing temperature data")

        return WeatherForecast(
            condition=condition,
            temp_min_c=float(temp_min),
            temp_max_c=float(temp_max),
            icon_type=_condition_to_icon(condition),
            location_name=location_id,
            humidity=report.get("humidityPercent"),
            wind_speed_kph=report.get("windSpeedKph"),
        )


register_provider("bbc", BBCWeatherProvider)
