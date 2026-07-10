"""
Playnite library import for Meridian Game Library.

Replaces steam_integration.py / gog_integration.py / epic_integration.py /
amazon_integration.py entirely. Rather than reimplementing (and repeatedly
failing to reliably reimplement) auth and library-sync for four different
storefronts, this now reads a JSON export written by a small Playnite
PowerShell extension (see the MeridianExporter folder) — Playnite already
has working, maintained Steam/GOG/Epic/Amazon integrations, so this app
Game Library just reads what Playnite already knows instead of
duplicating it.

Launching an installed game bypasses Playnite entirely when possible: the
exporter resolves each game's Play action via Playnite's own documented
ExpandGameVariables API (see MeridianExporter.psm1) — for a File-type
action that's a direct path to the real executable, for a URL-type action
it's often something Playnite itself resolved to, like
steam://rungameid/X or com.epicgames.launcher://..., which this app can
just hand off to directly. Only Emulator-type actions (or anything that
didn't resolve) fall back to asking Playnite to handle the launch via its
documented playnite://playnite/start/<id> URI.

Install/uninstall have no documented URI action to delegate to (confirmed
against Playnite's own GitHub issue tracker — it's a still-open feature
request as of this writing), so both open the game's page in Playnite via
playnite://playnite/showgame/<id> instead of pretending to trigger the
action directly. Same honesty standard as everywhere else in this
project: don't fabricate a URI action that isn't documented to exist.
"""

import json
import os
import subprocess
from pathlib import Path

import store

# Store-section id -> substrings to match against Playnite's Source field
# (case-insensitive). Playnite's own Source names vary a bit by version
# and by exactly how a library was imported, so this matches loosely
# rather than requiring an exact string. "other" isn't a real alias set —
# it's anything that doesn't match one of the other four, handled specially
# in _matches_store below.
SOURCE_ALIASES = {
    "steam": ["steam"],
    "gog": ["gog"],
    "epic": ["epic"],
    "amazon": ["amazon", "luna", "prime"],
}


def default_export_path():
    # Deliberately still "Meridian", not "Meridian Game Library" — this has
    # to match the folder the MeridianExporter Playnite extension already
    # writes to on disk (Join-Path $env:APPDATA "Meridian" in its .psm1).
    # Renaming this without also updating and reinstalling that extension
    # would silently break the pairing. Override via Settings if you do
    # rename the extension's own export folder to match.
    appdata = os.environ.get("APPDATA", str(Path.home() / "AppData" / "Roaming"))
    return str(Path(appdata) / "Meridian" / "playnite_library.json")


def get_export_path(playnite_settings):
    return playnite_settings.get("export_path") or default_export_path()


def export_file_available(playnite_settings):
    path = get_export_path(playnite_settings)
    return os.path.isfile(path)


def _load_raw_export(playnite_settings):
    path = get_export_path(playnite_settings)
    try:
        with open(path, encoding="utf-8-sig") as f:  # -sig: PowerShell's Out-File writes a BOM
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return None


def _matches_store(source, store_key):
    source = (source or "").lower()
    if store_key == "other":
        return not any(
            any(alias in source for alias in aliases)
            for aliases in SOURCE_ALIASES.values()
        )
    aliases = SOURCE_ALIASES.get(store_key, [store_key])
    return any(alias in source for alias in aliases)


def _entry_from_game(game):
    cover = game.get("CoverImagePath")
    return {
        "id": game.get("Id"),
        "title": game.get("Name") or "Untitled",
        "installed": bool(game.get("IsInstalled")),
        "art": cover if cover and os.path.isfile(cover) else None,
        "playtime_minutes": int((game.get("Playtime") or 0) / 60),
    }


def get_library(store_key, playnite_settings):
    """
    Returns entries for one section (steam/gog/epic/amazon/other), filtered
    from the shared Playnite export by matching Source against that
    store's known aliases. Returns None (distinct from []) if the export
    file itself isn't available yet, so the caller can tell "not
    connected" apart from "connected, but nothing from this store".
    """
    raw = _load_raw_export(playnite_settings)
    if raw is None:
        return None

    entries = [_entry_from_game(g) for g in raw if _matches_store(g.get("Source"), store_key)]
    entries.sort(key=lambda e: (not e["installed"], e["title"].lower()))
    return entries


def export_summary(playnite_settings):
    """
    Quick per-store counts, used by the Settings screen so the person can
    see at a glance whether the export is actually populated rather than
    just "connected" with zero useful data.
    """
    raw = _load_raw_export(playnite_settings)
    if raw is None:
        return None
    counts = {key: 0 for key in SOURCE_ALIASES}
    counts["other"] = 0
    for game in raw:
        source = (game.get("Source") or "").lower()
        matched = False
        for key, aliases in SOURCE_ALIASES.items():
            if any(alias in source for alias in aliases):
                counts[key] += 1
                matched = True
                break
        if not matched:
            counts["other"] += 1
    counts["total"] = len(raw)
    return counts


# --------------------------------------------------------------------------
# Actions
# --------------------------------------------------------------------------

def _find_raw_game(game_id, playnite_settings):
    raw = _load_raw_export(playnite_settings)
    if not raw:
        return None
    return next((g for g in raw if g.get("Id") == game_id), None)


def launch_game(game_id, playnite_settings):
    """
    Bypasses Playnite entirely when the exporter resolved a usable Play
    action (see module docstring). Falls back to asking Playnite to
    handle it — which does briefly start/show Playnite if it isn't
    already running — only when that resolution didn't give us something
    directly runnable.
    """
    game = _find_raw_game(game_id, playnite_settings)
    action_type = (game or {}).get("PlayActionType") or ""
    path = (game or {}).get("PlayActionPath")

    if path and action_type.lower() == "file" and os.path.isfile(path):
        args = (game.get("PlayActionArgs") or "").strip()
        workdir = game.get("PlayActionWorkDir") or os.path.dirname(path)
        try:
            # Splitting args naively on whitespace is good enough for the
            # common case; anything with quoted args-with-spaces falls
            # through to the exception handler below and on to Playnite.
            cmd = [path] + (args.split() if args else [])
            subprocess.Popen(cmd, cwd=workdir if os.path.isdir(workdir) else None)
            return
        except OSError:
            pass  # fall through to the playnite:// fallback below

    if path and action_type.lower() == "url":
        try:
            os.startfile(path)
            return
        except OSError:
            pass

    os.startfile(f"playnite://playnite/start/{game_id}")


def show_in_playnite(game_id):
    """
    Used for both install and uninstall: no documented URI action exists
    for either (unlike start), so this opens the game's page in Playnite
    for the person to finish there, rather than guessing at a URI that
    might not work.
    """
    os.startfile(f"playnite://playnite/showgame/{game_id}")
