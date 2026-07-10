"""Settings + controls JSON storage. Everything lives in the app's own
directory (not a hidden OS config folder), per spec: settings.json,
keyboard_controls.json, and controller_controls.json all sit in the program root.
"""

import json
import os
import sys
from pathlib import Path

from controller_input import DEFAULT_CONTROLS

# sys.frozen is set by PyInstaller. Path(__file__) resolves into a
# bundled/temporary location once compiled (not the folder the .exe
# actually lives in), which would silently reset settings every launch —
# using sys.executable's folder instead keeps this pointed at the real,
# persistent app folder in both source and compiled form.
if getattr(sys, "frozen", False):
    BASE_DIR = Path(sys.executable).resolve().parent
else:
    BASE_DIR = Path(__file__).resolve().parent

SETTINGS_FILE = BASE_DIR / "settings.json"
KEYBOARD_CONTROLS_FILE = BASE_DIR / "keyboard_controls.json"
CONTROLLER_CONTROLS_FILE = BASE_DIR / "controller_controls.json"
OVERLAY_FILE = BASE_DIR / "overlay.png"

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
        "background_image": None,
        "overlay_enabled": False,
        "overlay_image": None,
        "opening_video": None,
        "window_mode": "fullscreen",  # fullscreen | windowed
        "load_subfolders": True,
        "video_fullscreen": False,
        "battery_indicator": True,
        "playnite": {"export_path": None, "executable_path": None},
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
