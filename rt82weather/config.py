"""Configuration management for rt82weather.

Stores settings in ~/.config/rt82weather/config.json.
"""

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional

CONFIG_DIR = Path.home() / ".config" / "rt82weather"
CONFIG_FILE = CONFIG_DIR / "config.json"

DEFAULT_UPDATE_HOURS = 6


@dataclass
class Config:
    provider: str = "bbc"
    location_id: str = ""
    location_name: str = ""
    update_hours: int = DEFAULT_UPDATE_HOURS
    last_updated: Optional[str] = None
    insecure: bool = False

    @property
    def is_configured(self) -> bool:
        return bool(self.location_id)

    @property
    def last_updated_dt(self) -> Optional[datetime]:
        if self.last_updated:
            try:
                return datetime.fromisoformat(self.last_updated)
            except ValueError:
                return None
        return None

    def mark_updated(self) -> None:
        self.last_updated = datetime.now().isoformat(timespec="seconds")

    def needs_update(self) -> bool:
        dt = self.last_updated_dt
        if dt is None:
            return True
        elapsed = (datetime.now() - dt).total_seconds() / 3600
        return elapsed >= self.update_hours


def load_config() -> Config:
    if not CONFIG_FILE.exists():
        return Config()
    try:
        data = json.loads(CONFIG_FILE.read_text())
        return Config(**{k: v for k, v in data.items() if k in Config.__dataclass_fields__})
    except (json.JSONDecodeError, TypeError):
        return Config()


def save_config(cfg: Config) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(asdict(cfg), indent=2) + "\n")
