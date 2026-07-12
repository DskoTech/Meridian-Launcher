"""
Heroic Games Launcher library import for Meridian Game Library.

An alternative to playnite_import.py — Settings lets the person pick one
source or the other (game_import_source: "playnite" | "heroic"), never
both at once, since merging two independent library sources risks
duplicate/conflicting entries for the same game.

Heroic (github.com/Heroic-Games-Launcher/HeroicGamesLauncher) is an
Electron app; on Windows its config lives under
%APPDATA%\\heroic\\ (Electron's default userData path), with per-source
library caches:

  store_cache\\gog_library.json          - GOG library (via gogdl)
  store_cache\\legendary_library.json    - Epic library (via legendary)
  sideload_apps\\library.json            - manually-added/sideloaded games

This module reads those JSON files directly rather than calling Heroic's
CLI backends (legendary/gogdl), which keeps this simple but does mean the
data is only as fresh as Heroic's own last sync. Field names here are
based on Heroic's documented/public library schema — if a future Heroic
version renames things, get_library()'s defensive .get() chains should
degrade to empty/missing fields rather than crashing, but the exact
mapping is worth double-checking against a real install.

Launching goes through Heroic's own custom URI protocol
(heroic://launch/<runner>/<appName>), the same "let the real launcher's
own protocol handler do the complicated part" approach playnite_import.py
takes with Playnite — far less fragile than reimplementing
legendary/gogdl's launch invocation ourselves.
"""

import json
import os
import webbrowser
from pathlib import Path

# Heroic's "runner" names, which is how it identifies which backend a game
# belongs to for the heroic:// launch URI and per-source library files.
_RUNNER_FOR_STORE = {
    "epic": "legendary",
    "gog": "gog",
}
_LIBRARY_FILE_FOR_STORE = {
    "epic": "legendary_library.json",
    "gog": "gog_library.json",
}


def _heroic_config_dir():
    appdata = os.environ.get("APPDATA") or str(Path.home() / "AppData" / "Roaming")
    return Path(appdata) / "heroic"


def export_file_available(_heroic_settings=None):
    """Whether Heroic looks installed/configured at all — used the same
    way playnite_import.export_file_available() is, to drive the
    connected/not-connected state per store in Settings."""
    return (_heroic_config_dir() / "store_cache").is_dir()


def export_summary(_heroic_settings=None):
    d = _heroic_config_dir()
    return {"config_dir": str(d), "found": d.is_dir()}


def _load_json(path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return None


def _entry_from_legendary(game):
    # legendary_library.json entries are keyed by app_name with a nested
    # "app_title"/"install" block once Heroic has queried metadata for them.
    install = game.get("install") or {}
    art = None
    images = game.get("art_cover") or game.get("art_square")
    if images:
        art = images
    return {
        "id": game.get("app_name"),
        "title": game.get("app_title") or game.get("title") or "Untitled",
        "installed": bool(install.get("is_dlc") is False and install.get("install_path")) or bool(game.get("is_installed")),
        "art": art,
        "playtime_minutes": 0,  # Heroic tracks playtime separately per-runner; not read here
        "last_activity": None,
        "runner": "legendary",
    }


def _entry_from_gog(game):
    return {
        "id": game.get("app_name") or game.get("id"),
        "title": game.get("title") or "Untitled",
        "installed": bool(game.get("is_installed")),
        "art": game.get("art_cover") or game.get("art_square"),
        "playtime_minutes": 0,
        "last_activity": None,
        "runner": "gog",
    }


def _entry_from_sideload(game):
    return {
        "id": game.get("app_name") or game.get("title"),
        "title": game.get("title") or "Untitled",
        "installed": True,  # sideloaded entries are just a launch command, effectively always "installed"
        "art": game.get("art_cover") or game.get("art_square"),
        "playtime_minutes": 0,
        "last_activity": None,
        "runner": "sideload",
    }


def get_library(store_key, _heroic_settings=None):
    """Same contract as playnite_import.get_library(): returns entries for
    one section, or None if Heroic isn't set up at all (distinct from "set
    up but empty for this store"). Steam/Amazon aren't Heroic's domain —
    those return None here so the caller's normal "not connected" state
    shows, same as if Heroic simply doesn't support that store."""
    config_dir = _heroic_config_dir()
    if not config_dir.is_dir():
        return None

    if store_key == "epic":
        data = _load_json(config_dir / "store_cache" / "legendary_library.json")
        if data is None:
            return None
        games = data.get("library") if isinstance(data, dict) else data
        return [_entry_from_legendary(g) for g in (games or [])]

    if store_key == "gog":
        data = _load_json(config_dir / "store_cache" / "gog_library.json")
        if data is None:
            return None
        games = data.get("games") if isinstance(data, dict) else data
        return [_entry_from_gog(g) for g in (games or [])]

    if store_key == "other":
        data = _load_json(config_dir / "sideload_apps" / "library.json")
        if data is None:
            return []  # sideloaded apps are optional even when Heroic is set up
        games = data.get("games") if isinstance(data, dict) else data
        return [_entry_from_sideload(g) for g in (games or [])]

    # steam / amazon: not something Heroic manages
    return None


def launch_game(game_id, _heroic_settings=None, runner=None):
    """Hands off to Heroic's own heroic://launch/<runner>/<appName> deep
    link — Heroic must be installed and its protocol handler registered
    (both happen automatically with a normal Heroic install) for this to
    do anything. runner defaults to "legendary" (Epic) if not given; pass
    the "runner" field from the entry get_library() returned instead when
    you have it, since sideloaded/GOG entries need "sideload"/"gog"."""
    r = runner or "legendary"
    webbrowser.open(f"heroic://launch/{r}/{game_id}")


def show_in_launcher(game_id, runner=None):
    r = runner or "legendary"
    webbrowser.open(f"heroic://library/{r}/{game_id}")
