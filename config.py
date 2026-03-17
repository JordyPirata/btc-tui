"""User configuration — read/write config.json."""
from __future__ import annotations

import json
from pathlib import Path

CONFIG_FILE = Path("config.json")

DEFAULTS: dict = {
    "theme": "textual-dark",
}

THEMES = [
    "textual-dark",
    "textual-light",
    "nord",
    "gruvbox",
    "dracula",
    "tokyo-night",
    "monokai",
    "catppuccin-mocha",
    "catppuccin-latte",
    "flexoki",
    "rose-pine",
    "solarized-dark",
    "solarized-light",
    "atom-one-dark",
]


def load_config() -> dict:
    if not CONFIG_FILE.exists():
        save_config(DEFAULTS.copy())
        return DEFAULTS.copy()
    try:
        data = json.loads(CONFIG_FILE.read_text())
        return {**DEFAULTS, **data}
    except Exception:
        return DEFAULTS.copy()


def save_config(cfg: dict) -> None:
    CONFIG_FILE.write_text(json.dumps(cfg, indent=2))
