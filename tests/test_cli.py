"""Smoke tests for the CLI commands."""

from click.testing import CliRunner

from rt82weather.cli import main


class TestCLIHelp:
    def test_main_help(self):
        result = CliRunner().invoke(main, ["--help"])
        assert result.exit_code == 0
        assert "RT82 Weather" in result.output
        assert "-k" in result.output
        assert "--insecure" in result.output

    def test_version(self):
        result = CliRunner().invoke(main, ["--version"])
        assert result.exit_code == 0
        assert "rt82weather" in result.output

    def test_configure_help(self):
        result = CliRunner().invoke(main, ["configure", "--help"])
        assert result.exit_code == 0

    def test_update_help(self):
        result = CliRunner().invoke(main, ["update", "--help"])
        assert result.exit_code == 0
        assert "--force" in result.output

    def test_preview_help(self):
        result = CliRunner().invoke(main, ["preview", "--help"])
        assert result.exit_code == 0
        assert "--output" in result.output

    def test_install_help(self):
        result = CliRunner().invoke(main, ["install", "--help"])
        assert result.exit_code == 0

    def test_uninstall_help(self):
        result = CliRunner().invoke(main, ["uninstall", "--help"])
        assert result.exit_code == 0

    def test_status_help(self):
        result = CliRunner().invoke(main, ["status", "--help"])
        assert result.exit_code == 0


class TestCLIUnconfigured:
    def test_update_aborts_unconfigured(self, tmp_path, monkeypatch):
        monkeypatch.setattr("rt82weather.config.CONFIG_DIR", tmp_path)
        monkeypatch.setattr("rt82weather.config.CONFIG_FILE", tmp_path / "config.json")
        result = CliRunner().invoke(main, ["update"])
        assert result.exit_code != 0

    def test_preview_aborts_unconfigured(self, tmp_path, monkeypatch):
        monkeypatch.setattr("rt82weather.config.CONFIG_DIR", tmp_path)
        monkeypatch.setattr("rt82weather.config.CONFIG_FILE", tmp_path / "config.json")
        result = CliRunner().invoke(main, ["preview"])
        assert result.exit_code != 0
