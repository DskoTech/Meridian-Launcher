"""Settings + controls JSON storage.

BASE_DIR is still the folder the app itself lives in (used to find sibling
files like osm.bat and other Meridian .exe's sitting next to this one).
Actual user data - settings.json, the controls files, cached thumbnails,
etc - lives under %LOCALAPPDATA%\\Meridian Launcher\\ instead, so the app
folder can sit anywhere (including a read-only location like Program Files)
without losing write access to its own config.
"""

import json
import os
import shutil
from pathlib import Path

from controller_input import DEFAULT_CONTROLS

BASE_DIR = Path(__file__).resolve().parent

# All persistent user data (settings, controls, cached thumbnails) lives
# under %LOCALAPPDATA%\Meridian Launcher\ rather than next to the exe.
_local_appdata = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
DATA_DIR = Path(_local_appdata) / "Meridian Launcher"
DATA_DIR.mkdir(parents=True, exist_ok=True)

SETTINGS_FILE = DATA_DIR / "settings.json"
KEYBOARD_CONTROLS_FILE = DATA_DIR / "keyboard_controls.json"
CONTROLLER_CONTROLS_FILE = DATA_DIR / "controller_controls.json"
OVERLAY_FILE = DATA_DIR / "overlay.png"


def _migrate_legacy_file(old_path, new_path):
    """One-time migration: if a pre-update install left a data file sitting
    next to the exe and nothing has been written to the new location yet,
    carry it over so existing users don't lose their settings."""
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
        # each item: {"path": ..., "name": ...}
        # launch_with_osm: whether launching an item from this section also
        # runs osm.bat (on-screen-menu companion script) — on by default
        # for every section except Games, since games are usually played
        # with the controller captured by the game itself rather than
        # needing the on-screen menu overlay running alongside them.
        sections[sid] = {"items": [], "launch_with_osm": sid != "games"}
    sections["macros"] = {"items": []}  # each item: {"type": "bat", "path": ..., "name": ...}

    return {
        "folders": {"music": [], "photos": [], "videos": []},
        "sections": sections,
        "custom_sections": [],  # [{"id": "...", "label": "..."}]
        "web_shortcuts": [],  # [{"url": "...", "label": "..."}] — user-added, opened in CyberDeckBrowser
        "macros_whitelist": ["onscreenmenu.exe"],
        "background_image": None,
        "overlay_enabled": False,
        "overlay_image": None,
        "opening_video": None,
        "window_mode": "windowed_fullscreen",  # exclusive_fullscreen | windowed_fullscreen | windowed | kiosk
        "layout": "dawning_horizon",  # dawning_horizon | night_horizon | cyber_radial
        "recent_games": [],  # [{"path": ..., "name": ...}], most-recent-first, capped at 5
        "display_type": {"games": "gallery"},  # per-section-id: "list" | "gallery"; any id not present defaults to "list"
        "desktop_section_enabled": False,  # Desktop: always first in the list when on, off by default
        "load_subfolders": True,
        "video_fullscreen": False,
        "battery_indicator": True,
        "auto_shuffle_songs": True,  # when a song ends, load a random one instead of the next in list order
        # Global toggle: also run osm.bat when System section items that
        # shell out to Windows (Task Manager, Control Panel, Recycle Bin,
        # Uninstall Apps, "open Windows Bluetooth settings") are used.
        "launch_system_with_osm": True,
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
            return merged
        except Exception:
            pass
    s = default_settings()
    save_settings(s)
    return s


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
        return merged
    except Exception:
        return dict(DEFAULT_CONTROLS)


def display_name(path: str) -> str:
    """Strip directory and extension: C:/chrome.exe -> chrome"""
    return Path(path).stem


def slugify(name: str) -> str:
    slug = "".join(c.lower() if c.isalnum() else "-" for c in name).strip("-")
    while "--" in slug:
        slug = slug.replace("--", "-")
    return slug or "section"
