"""Command-line interface for RT82 Weather."""

import platform
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path

import click

from . import __version__
from .config import Config, load_config, save_config
from .theme import (
    console, success, error, warning, info, muted,
    print_header, print_banner,
)

# Ensure BBC provider is registered on import
from .providers import bbc as _bbc_side_effect  # noqa: F401
from .providers import get_provider, list_providers


@click.group()
@click.version_option(version=__version__, prog_name="rt82weather")
def main():
    """RT82 Weather - Weather on your keyboard."""
    pass


# ---------------------------------------------------------------------------
# configure
# ---------------------------------------------------------------------------

@main.command()
@click.option("--provider", default=None, help="Weather provider (default: bbc)")
@click.option("--hours", default=None, type=int, help="Update interval in hours (default: 6)")
def configure(provider: str | None, hours: int | None):
    """Search for your city and save the weather location."""
    print_banner()
    console.print()

    cfg = load_config()

    if provider:
        cfg.provider = provider
    if hours:
        cfg.update_hours = hours

    prov = get_provider(cfg.provider)
    info(f"Using provider: [highlight]{prov.name}[/highlight]")
    console.print()

    query = click.prompt("Search for a city")
    console.print()

    muted("  Searching...")
    try:
        locations = prov.search_location(query)
    except Exception as e:
        error(f"Search failed: {e}")
        raise click.Abort()

    if not locations:
        warning("No locations found. Try a different search term.")
        raise click.Abort()

    print_header("Results", "\U0001f4cd")
    for i, loc in enumerate(locations[:15], 1):
        console.print(f"  [info]{i:2d}.[/info] {loc.display_name}")

    console.print()
    choice = click.prompt(
        "Pick a number",
        type=click.IntRange(1, min(len(locations), 15)),
    )
    selected = locations[choice - 1]

    cfg.location_id = selected.id
    cfg.location_name = selected.display_name
    save_config(cfg)

    console.print()
    success(f"Saved: [highlight]{selected.display_name}[/highlight]")
    muted(f"  Provider: {cfg.provider}  |  ID: {selected.id}  |  Update every {cfg.update_hours}h")


# ---------------------------------------------------------------------------
# update
# ---------------------------------------------------------------------------

@main.command()
@click.option("--force", is_flag=True, help="Update even if recently updated")
def update(force: bool):
    """Fetch weather and upload to the RT82 keyboard display."""
    print_banner()
    console.print()

    cfg = load_config()
    if not cfg.is_configured:
        error("Not configured yet. Run: rt82weather configure")
        raise click.Abort()

    if not force and not cfg.needs_update():
        dt = cfg.last_updated_dt
        info(f"Already up-to-date (last updated {dt:%H:%M}). Use --force to override.")
        return

    print_header("Fetching Weather", "\u2601\ufe0f")
    muted(f"  Location: {cfg.location_name}")
    muted(f"  Provider: {cfg.provider}")

    prov = get_provider(cfg.provider)
    try:
        forecast = prov.get_forecast(cfg.location_id)
    except Exception as e:
        error(f"Failed to fetch weather: {e}")
        raise click.Abort()

    forecast.location_name = cfg.location_name
    info(f"{forecast.condition.capitalize()}  {forecast.temp_min_c:.0f}°/{forecast.temp_max_c:.0f}°C")

    print_header("Rendering", "\U0001f3a8")
    from .render import render_weather
    img = render_weather(forecast)

    print_header("Encoding QGIF", "\U0001f4e6")
    from rt82display.cli import encode_frames_to_qgif, upload_to_device

    with tempfile.NamedTemporaryFile(suffix=".qgif", delete=False) as tmp_qgif:
        tmp_qgif_path = Path(tmp_qgif.name)

    try:
        if not encode_frames_to_qgif([img], tmp_qgif_path, fps=2):
            error("QGIF encoding failed")
            raise click.Abort()

        qgif_data = bytearray(tmp_qgif_path.read_bytes())
        if len(qgif_data) > 5 and qgif_data[5] == 0x05:
            qgif_data[5] = 0x03

        data = bytes(qgif_data)
        muted(f"  QGIF size: {len(data):,} bytes")

        print_header("Uploading", "\U0001f4e4")
        upload_to_device(data, frame_count=1)

        cfg.mark_updated()
        save_config(cfg)

        console.print()
        success("Weather uploaded!")

    except FileNotFoundError as e:
        console.print()
        error(str(e))
        raise click.Abort()
    except ConnectionError as e:
        console.print()
        error(f"Connection failed: {e}")
        raise click.Abort()
    except Exception as e:
        console.print()
        error(f"Upload failed: {e}")
        raise click.Abort()
    finally:
        tmp_qgif_path.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# preview
# ---------------------------------------------------------------------------

@main.command()
@click.option("-o", "--output", default="weather_preview.png",
              type=click.Path(), help="Output PNG path")
def preview(output: str):
    """Generate the weather image without uploading."""
    print_banner()
    console.print()

    cfg = load_config()
    if not cfg.is_configured:
        error("Not configured yet. Run: rt82weather configure")
        raise click.Abort()

    print_header("Fetching Weather", "\u2601\ufe0f")
    muted(f"  Location: {cfg.location_name}")

    prov = get_provider(cfg.provider)
    try:
        forecast = prov.get_forecast(cfg.location_id)
    except Exception as e:
        error(f"Failed to fetch weather: {e}")
        raise click.Abort()

    forecast.location_name = cfg.location_name
    info(f"{forecast.condition.capitalize()}  {forecast.temp_min_c:.0f}°/{forecast.temp_max_c:.0f}°C")

    print_header("Rendering", "\U0001f3a8")
    from .render import render_weather
    img = render_weather(forecast)
    img.save(output, "PNG")

    console.print()
    success(f"Saved preview: [highlight]{output}[/highlight]")
    muted(f"  {img.width}x{img.height} pixels")


# ---------------------------------------------------------------------------
# install / uninstall
# ---------------------------------------------------------------------------

_SYSTEMD_SERVICE_DIR = Path.home() / ".config" / "systemd" / "user"
_SYSTEMD_SERVICE_NAME = "rt82weather"
_LAUNCHD_PLIST_DIR = Path.home() / "Library" / "LaunchAgents"
_LAUNCHD_LABEL = "com.rt82weather.update"


def _find_rt82weather_bin() -> str:
    found = shutil.which("rt82weather")
    if found:
        return found
    return sys.executable + " -m rt82weather.cli"


def _write_systemd_units(update_hours: int) -> None:
    _SYSTEMD_SERVICE_DIR.mkdir(parents=True, exist_ok=True)
    bin_path = _find_rt82weather_bin()

    service = _SYSTEMD_SERVICE_DIR / f"{_SYSTEMD_SERVICE_NAME}.service"
    service.write_text(
        f"[Unit]\n"
        f"Description=Update RT82 keyboard weather display\n\n"
        f"[Service]\n"
        f"Type=oneshot\n"
        f"ExecStart={bin_path} update --force\n"
    )

    timer = _SYSTEMD_SERVICE_DIR / f"{_SYSTEMD_SERVICE_NAME}.timer"
    timer.write_text(
        f"[Unit]\n"
        f"Description=Update RT82 weather display every {update_hours}h\n\n"
        f"[Timer]\n"
        f"OnBootSec=1min\n"
        f"OnUnitActiveSec={update_hours}h\n"
        f"Persistent=true\n\n"
        f"[Install]\n"
        f"WantedBy=timers.target\n"
    )


def _write_launchd_plist(update_hours: int) -> None:
    _LAUNCHD_PLIST_DIR.mkdir(parents=True, exist_ok=True)
    bin_path = _find_rt82weather_bin()
    interval_sec = update_hours * 3600

    plist = _LAUNCHD_PLIST_DIR / f"{_LAUNCHD_LABEL}.plist"
    plist.write_text(
        f'<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"'
        f' "http://www.apple.com/DTDs/PropertyList-1.0.dtd">\n'
        f'<plist version="1.0">\n'
        f'<dict>\n'
        f'  <key>Label</key>\n'
        f'  <string>{_LAUNCHD_LABEL}</string>\n'
        f'  <key>ProgramArguments</key>\n'
        f'  <array>\n'
        f'    <string>{bin_path}</string>\n'
        f'    <string>update</string>\n'
        f'    <string>--force</string>\n'
        f'  </array>\n'
        f'  <key>StartInterval</key>\n'
        f'  <integer>{interval_sec}</integer>\n'
        f'  <key>RunAtLoad</key>\n'
        f'  <true/>\n'
        f'</dict>\n'
        f'</plist>\n'
    )


@main.command()
def install():
    """Install a recurring service to update weather automatically."""
    print_banner()
    console.print()

    cfg = load_config()
    if not cfg.is_configured:
        error("Not configured yet. Run: rt82weather configure")
        raise click.Abort()

    system = platform.system()

    if system == "Linux":
        print_header("Installing systemd timer", "\u2699\ufe0f")
        _write_systemd_units(cfg.update_hours)
        subprocess.run(
            ["systemctl", "--user", "daemon-reload"],
            check=False,
        )
        subprocess.run(
            ["systemctl", "--user", "enable", "--now", f"{_SYSTEMD_SERVICE_NAME}.timer"],
            check=False,
        )
        console.print()
        success("Systemd timer installed and started")
        muted(f"  Updates every {cfg.update_hours} hours")
        muted(f"  Check with: systemctl --user status {_SYSTEMD_SERVICE_NAME}.timer")

    elif system == "Darwin":
        print_header("Installing launchd agent", "\u2699\ufe0f")
        _write_launchd_plist(cfg.update_hours)
        plist_path = _LAUNCHD_PLIST_DIR / f"{_LAUNCHD_LABEL}.plist"
        subprocess.run(["launchctl", "unload", str(plist_path)], check=False,
                       capture_output=True)
        subprocess.run(["launchctl", "load", str(plist_path)], check=False)
        console.print()
        success("Launch agent installed and loaded")
        muted(f"  Updates every {cfg.update_hours} hours")
        muted(f"  Plist: {plist_path}")

    else:
        error(f"Unsupported platform: {system}")
        raise click.Abort()


@main.command()
def uninstall():
    """Remove the automatic weather update service."""
    print_banner()
    console.print()

    system = platform.system()

    if system == "Linux":
        print_header("Removing systemd timer", "\U0001f5d1\ufe0f")
        subprocess.run(
            ["systemctl", "--user", "disable", "--now", f"{_SYSTEMD_SERVICE_NAME}.timer"],
            check=False,
        )
        for ext in ("service", "timer"):
            path = _SYSTEMD_SERVICE_DIR / f"{_SYSTEMD_SERVICE_NAME}.{ext}"
            if path.exists():
                path.unlink()
                muted(f"  Removed {path}")
        subprocess.run(["systemctl", "--user", "daemon-reload"], check=False)
        console.print()
        success("Systemd timer removed")

    elif system == "Darwin":
        print_header("Removing launchd agent", "\U0001f5d1\ufe0f")
        plist_path = _LAUNCHD_PLIST_DIR / f"{_LAUNCHD_LABEL}.plist"
        if plist_path.exists():
            subprocess.run(["launchctl", "unload", str(plist_path)], check=False,
                           capture_output=True)
            plist_path.unlink()
            muted(f"  Removed {plist_path}")
        console.print()
        success("Launch agent removed")

    else:
        error(f"Unsupported platform: {system}")
        raise click.Abort()


# ---------------------------------------------------------------------------
# status
# ---------------------------------------------------------------------------

@main.command()
def status():
    """Show current configuration and service state."""
    print_banner()
    console.print()

    cfg = load_config()

    print_header("Configuration", "\u2699\ufe0f")

    if not cfg.is_configured:
        warning("Not configured. Run: rt82weather configure")
        return

    console.print(f"  [tertiary]Location:[/tertiary]  {cfg.location_name}")
    console.print(f"  [tertiary]Provider:[/tertiary]  {cfg.provider}")
    console.print(f"  [tertiary]Location ID:[/tertiary]  {cfg.location_id}")
    console.print(f"  [tertiary]Interval:[/tertiary]  every {cfg.update_hours}h")

    if cfg.last_updated_dt:
        console.print(f"  [tertiary]Last update:[/tertiary]  {cfg.last_updated_dt:%Y-%m-%d %H:%M}")
        if cfg.needs_update():
            warning("Update is due")
        else:
            success("Up to date")
    else:
        muted("  Never updated")

    system = platform.system()
    console.print()
    print_header("Service", "\U0001f504")

    if system == "Linux":
        timer_path = _SYSTEMD_SERVICE_DIR / f"{_SYSTEMD_SERVICE_NAME}.timer"
        if timer_path.exists():
            result = subprocess.run(
                ["systemctl", "--user", "is-active", f"{_SYSTEMD_SERVICE_NAME}.timer"],
                capture_output=True, text=True,
            )
            state = result.stdout.strip()
            if state == "active":
                success(f"Systemd timer is [highlight]active[/highlight]")
            else:
                warning(f"Systemd timer state: {state}")
        else:
            muted("  Systemd timer not installed. Run: rt82weather install")

    elif system == "Darwin":
        plist_path = _LAUNCHD_PLIST_DIR / f"{_LAUNCHD_LABEL}.plist"
        if plist_path.exists():
            result = subprocess.run(
                ["launchctl", "list", _LAUNCHD_LABEL],
                capture_output=True, text=True,
            )
            if result.returncode == 0:
                success("Launch agent is [highlight]loaded[/highlight]")
            else:
                warning("Launch agent plist exists but is not loaded")
        else:
            muted("  Launch agent not installed. Run: rt82weather install")

    else:
        muted(f"  Service management not supported on {system}")


if __name__ == "__main__":
    main()
