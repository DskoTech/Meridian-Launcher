"""Settings + controls JSON storage.

BASE_DIR is still the folder the app itself lives in (used to find sibling
exes/scripts). Actual user data - settings.json, the controls files,
cached thumbnails, etc - lives under
%LOCALAPPDATA%\\Meridian Launcher\\Meridian Game Library\\ instead, so the
app folder can sit anywhere without losing write access to its own config.
"""

import json
import os
import shutil
import sys
from pathlib import Path

from controller_input import DEFAULT_CONTROLS

# sys.frozen is set by PyInstaller. Path(__file__) resolves into a
# bundled/temporary location once compiled (not the folder the .exe
# actually lives in) — using sys.executable's folder instead keeps BASE_DIR
# pointed at the real app folder in both source and compiled form.
if getattr(sys, "frozen", False):
    BASE_DIR = Path(sys.executable).resolve().parent
else:
    BASE_DIR = Path(__file__).resolve().parent

# All persistent user data (settings, controls, cached thumbnails) lives
# under %LOCALAPPDATA%\Meridian Launcher\Meridian Game Library\ rather than
# next to the exe.
_local_appdata = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
DATA_DIR = Path(_local_appdata) / "Meridian Launcher" / "Meridian Game Library"
DATA_DIR.mkdir(parents=True, exist_ok=True)

SETTINGS_FILE = DATA_DIR / "settings.json"
KEYBOARD_CONTROLS_FILE = DATA_DIR / "keyboard_controls.json"
CONTROLLER_CONTROLS_FILE = DATA_DIR / "controller_controls.json"
OVERLAY_FILE = DATA_DIR / "overlay.png"
ASSETS_DIR = DATA_DIR / "theme_assets"
ASSETS_DIR.mkdir(parents=True, exist_ok=True)


def _migrate_legacy_file(old_path, new_path):
    """One-time migration: carry a pre-update data file sitting next to the
    exe over to the new location, if the new location doesn't have one yet."""
    try:
        if old_path.exists() and not new_path.exists():
            shutil.copy2(old_path, new_path)
    except Exception:
        pass


for _old, _new in (
    (BASE_DIR / "settings.json", SETTINGS_FILE),
    (BASE_DIR / "keyboard_controls.json", KEYBOARD_CONTROLS_FILE),
    (BASE_DIR / "controller_controls.json", CONTROLLER_CONTROLS_FILE),
    (BASE_DIR / "overlay.png", OVERLAY_FILE),
):
    _migrate_legacy_file(_old, _new)

# Fixed sections that use a simple "list of launchable .exe" model.
EXE_LIST_SECTIONS = ["apps", "games", "emulators", "chat", "streaming"]

DEFAULT_KEYBOARD_CONTROLS = {
    "confirm": "Enter",
    "back": "Space",
    "up": "ArrowUp",
    "down": "ArrowDown",
    "left": "ArrowLeft",
    "right": "ArrowRight",
    # Escape is hardcoded to quit the whole app and is not remappable here.
}


def default_settings():
    sections = {}
    for sid in EXE_LIST_SECTIONS:
        sections[sid] = {"items": []}  # each item: {"path": ..., "name": ...}
    sections["macros"] = {"items": []}  # each item: {"type": "bat", "path": ..., "name": ...}

    return {
        "folders": {"music": [], "photos": [], "videos": []},
        "sections": sections,
        "custom_sections": [],  # [{"id": "...", "label": "..."}]
        "macros_whitelist": ["onscreenmenu.exe"],
        "background_by_theme": {},
        "overlay_by_theme": {},
        "overlay_enabled_by_theme": {},
        "background_image": None,
        "overlay_enabled": False,
        "overlay_image": None,
        "opening_video": None,
        "window_mode": "exclusive_fullscreen",  # exclusive_fullscreen | windowed_fullscreen | windowed | kiosk
        # When a game launches: always focus it to the foreground once its
        # window appears, then either minimize Game Library (False,
        # default) or close it outright (True) - see _watch_and_focus_game.
        "close_game_library_on_launch": False,
        # Controller Bridge: per-game (not global - see toggle_
        # controller_bridge_for_game's docstring in main.py for why),
        # translates real controller input into keyboard presses only
        # while a specific game that needs it is actually running.
        "controller_bridge_games": [],
        "controller_bridge_mapping_path": None,
        "layout": "dawning_horizon",  # dawning_horizon | night_horizon | cyber_radial
        # Dawning Horizon background hue: "original", or "<palette>:<hue>"
        # where palette is light|dark|neon|primary|pastel|bubblegum and hue
        # is red|orange|yellow|green|blue|indigo|violet. Purely a frontend
        # concern (app.js computes and applies the actual colors).
        "dawning_theme_color": "original",
        # When on, each saved Playnite filter preset (exported by the
        # MeridianExporter extension) becomes its own section in the
        # category row, named after the preset.
        # On by default: anything other than Steam/GOG/Epic/Amazon(/Luna)
        # gets its own section (one per distinct Playnite Source string)
        # instead of all being lumped into a single "Other" bucket.
        "other_source_sections": True,
        "close_tasks_without_prompt": False,
        # How to bring the app to the foreground when it's in the background:
        # "start_select" (Start+Select together), "xbox" (Guide button, when
        # the controller/backend reports it), or "off".
        "foreground_trigger": "start_select",
        # Force the XInput backend instead of GameInput. XInput is the
        # battle-tested path; GameInput adds Guide-button reporting and
        # broader native device support on Win11.
        "prefer_xinput": False,
        # Start-menu game management: hidden titles are dropped from every
        # game section unless show_hidden_games is on; renames replace the
        # displayed title without touching Playnite's own data.
        "hidden_games": [],  # [playnite game id, ...]
        "game_renames": {},  # {game id: custom display name}
        "show_hidden_games": False,
        "load_subfolders": True,
        "video_fullscreen": False,
        "battery_indicator": True,
        "games_per_row": 5,  # 3 | 4 | 5
        "display_type": {},  # per-store-id: "gallery" (default) | "list"
        "pull_custom_sections_from_playnite": False,
        "playnite": {"export_path": None, "executable_path": None},
        "game_import_source": "playnite",  # "playnite" | "heroic" — never both at once
    }


def load_settings():
    if SETTINGS_FILE.exists():
        try:
            data = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
            # Migrate installs saved by the earlier version, which nested
            # macros_whitelist under "sections" by mistake. Carry the user's
            # actual saved list forward instead of discarding it.
            legacy_whitelist = data.get("sections", {}).pop("macros_whitelist", None)
            if legacy_whitelist and "macros_whitelist" not in data:
                data["macros_whitelist"] = legacy_whitelist
            merged = default_settings()
            _deep_merge(merged, data)
            _migrate_theme_media(merged)
            return merged
        except Exception:
            pass
    s = default_settings()
    save_settings(s)
    return s


def _migrate_theme_media(m):
    if m.get("background_image") and not m.get("background_by_theme"):
        m["background_by_theme"] = {"dawning_horizon": m["background_image"]}
    if m.get("overlay_image") and not m.get("overlay_by_theme"):
        m["overlay_by_theme"] = {"dawning_horizon": m["overlay_image"]}
        m["overlay_enabled_by_theme"] = {"dawning_horizon": bool(m.get("overlay_enabled"))}


def _deep_merge(base, override):
    for k, v in override.items():
        if isinstance(v, dict) and isinstance(base.get(k), dict):
            _deep_merge(base[k], v)
        else:
            base[k] = v


def save_settings(s):
    SETTINGS_FILE.write_text(json.dumps(s, indent=2), encoding="utf-8")


def ensure_controls_files():
    if not KEYBOARD_CONTROLS_FILE.exists():
        KEYBOARD_CONTROLS_FILE.write_text(json.dumps(DEFAULT_KEYBOARD_CONTROLS, indent=2), encoding="utf-8")
    if not CONTROLLER_CONTROLS_FILE.exists():
        CONTROLLER_CONTROLS_FILE.write_text(json.dumps(DEFAULT_CONTROLS, indent=2), encoding="utf-8")


def load_keyboard_controls():
    try:
        data = json.loads(KEYBOARD_CONTROLS_FILE.read_text(encoding="utf-8"))
        merged = dict(DEFAULT_KEYBOARD_CONTROLS)
        merged.update(data)
        return merged
    except Exception:
        return dict(DEFAULT_KEYBOARD_CONTROLS)


def load_controller_controls():
    try:
        data = json.loads(CONTROLLER_CONTROLS_FILE.read_text(encoding="utf-8"))
        merged = dict(DEFAULT_CONTROLS)
        merged.update(data)
    except Exception:
        merged = dict(DEFAULT_CONTROLS)
    # quit_combo (L3+R3) is fully removed, not just re-defaulted to empty -
    # there's no Settings UI to customize it, so anything already on disk
    # here is leftover factory-default cruft from before removal, never a
    # deliberate user choice. Forcing it off unconditionally (rather than
    # relying on the merge above) means it actually goes away for anyone
    # who already has an old controller_controls.json written to
    # %LOCALAPPDATA%, not just fresh installs.
    merged["quit_combo"] = []
    return merged


def display_name(path: str) -> str:
    """Strip directory and extension: C:/chrome.exe -> chrome"""
    return Path(path).stem


def slugify(name: str) -> str:
    slug = "".join(c.lower() if c.isalnum() else "-" for c in name).strip("-")
    while "--" in slug:
        slug = slug.replace("--", "-")
    return slug or "section"
