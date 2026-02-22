"""Crush color theme for Rich console output.

Same palette as rt82display for a consistent look across tools.
"""

from rich.console import Console
from rich.theme import Theme
from rich.panel import Panel

CRUSH_THEME = Theme({
    "success": "#12C78F",
    "error": "#EB4268",
    "warning": "#E8FE96",
    "info": "#00A4FF",
    "primary": "#6B50FF",
    "secondary": "#FF60FF",
    "tertiary": "#68FFD6",
    "accent": "#E8FE96",
    "muted": "#858392",
    "subtle": "#605F6B",
    "highlight": "#F1EFEF",
    "coral": "#FF577D",
    "julep": "#00FFB2",
    "cumin": "#BF976F",
})

console = Console(theme=CRUSH_THEME)


def success(message: str) -> None:
    console.print(f"[success]\u2705[/success] {message}")


def error(message: str) -> None:
    console.print(f"[error]\u274c[/error] {message}")


def warning(message: str) -> None:
    console.print(f"[warning]\u26a0\ufe0f[/warning] {message}")


def info(message: str) -> None:
    console.print(f"[info]\U0001f4a1[/info] {message}")


def muted(message: str) -> None:
    console.print(f"[muted]{message}[/muted]")


def print_header(title: str, emoji: str = "") -> None:
    console.print()
    prefix = f"{emoji} " if emoji else ""
    console.rule(f"[primary]{prefix}{title}[/primary]", style="primary")
    console.print()


def print_banner() -> None:
    console.print(Panel.fit(
        "\u2601\ufe0f [primary]RT82 Weather[/primary] \u203a Weather on your keyboard",
        border_style="primary"
    ))
