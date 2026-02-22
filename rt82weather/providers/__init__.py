"""Weather provider interface and data types."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class IconType(Enum):
    SUN = "sun"
    PARTLY_CLOUDY = "partly_cloudy"
    CLOUD = "cloud"
    RAIN = "rain"
    SNOW = "snow"
    THUNDERSTORM = "thunderstorm"
    MIST = "mist"


@dataclass
class Location:
    id: str
    name: str
    area: str
    country: str

    @property
    def display_name(self) -> str:
        return f"{self.name}, {self.area}, {self.country}"


@dataclass
class WeatherForecast:
    condition: str
    temp_min_c: float
    temp_max_c: float
    icon_type: IconType
    location_name: str = ""
    humidity: Optional[float] = None
    wind_speed_kph: Optional[float] = None


class WeatherProvider(ABC):
    name: str = ""

    @abstractmethod
    def search_location(self, query: str) -> list[Location]:
        ...

    @abstractmethod
    def get_forecast(self, location_id: str) -> WeatherForecast:
        ...


_PROVIDERS: dict[str, type[WeatherProvider]] = {}


def register_provider(name: str, cls: type[WeatherProvider]) -> None:
    _PROVIDERS[name] = cls


def get_provider(name: str) -> WeatherProvider:
    cls = _PROVIDERS.get(name)
    if cls is None:
        raise ValueError(f"Unknown provider: {name!r}. Available: {list(_PROVIDERS)}")
    return cls()


def list_providers() -> list[str]:
    return list(_PROVIDERS)
