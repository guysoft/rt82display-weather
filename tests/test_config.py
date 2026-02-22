"""Tests for configuration loading, saving, and state logic."""

import json
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from rt82weather.config import Config, load_config, save_config, CONFIG_FILE


@pytest.fixture(autouse=True)
def isolate_config(tmp_path, monkeypatch):
    """Redirect config to a temp directory so tests never touch real config."""
    cfg_dir = tmp_path / "rt82weather"
    cfg_file = cfg_dir / "config.json"
    monkeypatch.setattr("rt82weather.config.CONFIG_DIR", cfg_dir)
    monkeypatch.setattr("rt82weather.config.CONFIG_FILE", cfg_file)
    return cfg_file


class TestConfigDefaults:
    def test_defaults(self):
        cfg = Config()
        assert cfg.provider == "bbc"
        assert cfg.location_id == ""
        assert cfg.update_hours == 6
        assert cfg.insecure is False

    def test_not_configured_by_default(self):
        assert not Config().is_configured

    def test_configured_with_location(self):
        cfg = Config(location_id="123")
        assert cfg.is_configured


class TestConfigTimestamps:
    def test_last_updated_dt_none(self):
        assert Config().last_updated_dt is None

    def test_last_updated_dt_valid(self):
        cfg = Config(last_updated="2026-01-15T10:30:00")
        assert cfg.last_updated_dt == datetime(2026, 1, 15, 10, 30, 0)

    def test_last_updated_dt_invalid(self):
        cfg = Config(last_updated="not-a-date")
        assert cfg.last_updated_dt is None

    def test_mark_updated(self):
        cfg = Config()
        assert cfg.last_updated is None
        cfg.mark_updated()
        assert cfg.last_updated is not None
        dt = cfg.last_updated_dt
        assert (datetime.now() - dt).total_seconds() < 5

    def test_needs_update_never_updated(self):
        assert Config().needs_update() is True

    def test_needs_update_recently(self):
        cfg = Config(update_hours=6)
        cfg.mark_updated()
        assert cfg.needs_update() is False

    def test_needs_update_stale(self):
        old = (datetime.now() - timedelta(hours=7)).isoformat(timespec="seconds")
        cfg = Config(update_hours=6, last_updated=old)
        assert cfg.needs_update() is True


class TestConfigPersistence:
    def test_save_and_load(self, isolate_config):
        cfg = Config(provider="bbc", location_id="42", location_name="London",
                     update_hours=3, insecure=True)
        save_config(cfg)
        assert isolate_config.exists()

        loaded = load_config()
        assert loaded.provider == "bbc"
        assert loaded.location_id == "42"
        assert loaded.location_name == "London"
        assert loaded.update_hours == 3
        assert loaded.insecure is True

    def test_load_missing_file(self):
        cfg = load_config()
        assert cfg.provider == "bbc"
        assert cfg.location_id == ""

    def test_load_corrupt_json(self, isolate_config):
        isolate_config.parent.mkdir(parents=True, exist_ok=True)
        isolate_config.write_text("NOT JSON{{{")
        cfg = load_config()
        assert cfg.provider == "bbc"

    def test_load_ignores_unknown_keys(self, isolate_config):
        isolate_config.parent.mkdir(parents=True, exist_ok=True)
        isolate_config.write_text(json.dumps({"provider": "bbc", "unknown_key": 99}))
        cfg = load_config()
        assert cfg.provider == "bbc"
