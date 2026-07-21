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
ASSETS_DIR = DATA_DIR / "theme_assets"
ASSETS_DIR.mkdir(parents=True, exist_ok=True)


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
        # Built-in fixed sections (Music/Photos/Videos/Apps/Games/
        # Emulators/Chat/Streaming/Web/Files/Macros) a person has chosen
        # to hide from the sections bar entirely. Empty by default - all
        # visible, same as always.
        "hidden_builtin_sections": [],
        # Discovered Plugins/ folders: {plugin_id: {"visible": bool}}.
        # Hidden by default; populated/merged by plugin_manager.scan_plugins()
        # on startup and via the Settings > Plugins "Rescan" button.
        "plugins": {},
        "web_shortcuts": [],  # [{"url": "...", "label": "..."}] — user-added, opened in CyberDeckBrowser
        "macros_whitelist": ["onscreenmenu.exe"],
        # Per-theme background & overlay: {layout_key: path}. Empty means
        # "use that theme's rendered placeholder". Legacy single-value keys
        # below are migrated into the dawning_horizon slot on first load.
        "background_by_theme": {},   # {dawning_horizon|night_horizon|cyber_radial: path}
        "overlay_by_theme": {},      # same shape
        "overlay_enabled_by_theme": {},
        # legacy (migrated, then ignored):
        "background_image": None,
        "overlay_enabled": False,
        "overlay_image": None,
        "opening_video": None,
        "window_mode": "exclusive_fullscreen",  # exclusive_fullscreen | windowed_fullscreen | windowed | kiosk
        "layout": "dawning_horizon",  # dawning_horizon | night_horizon | cyber_radial
        # Dawning Horizon background hue: "original", or "<palette>:<hue>"
        # where palette is light|dark|neon|primary|pastel|bubblegum and hue
        # is red|orange|yellow|green|blue|indigo|violet. Purely a frontend
        # concern (app.js computes and applies the actual colors).
        "dawning_theme_color": "original",
        # Open-programs bar: skip the hold-X close confirmation
        "close_tasks_without_prompt": False,
        # How to bring the app to the foreground when it's in the background:
        # "start_select" (Start+Select together), "xbox" (Guide button, when
        # the controller/backend reports it), or "off".
        "foreground_trigger": "start_select",
        # Force the XInput backend instead of GameInput. XInput is the
        # battle-tested path; GameInput adds Guide-button reporting and
        # broader native device support on Win11.
        "prefer_xinput": False,
        # "xinput" (default), "gameinput", "directinput", "sdl3", or "auto"
        # (try all four, XInput first). Settings > Controls cycles this;
        # prefer_xinput above is the older on/off toggle, kept for anyone
        # who already has it set, but input_backend is authoritative now.
        # Default is "auto" rather than a hard "xinput" lock: XInput is
        # still tried first (so Xbox-compatible pads behave exactly as
        # before), but a PlayStation controller — which never speaks
        # XInput at all — now falls through to DirectInput/SDL3
        # automatically instead of silently looking like "no controller"
        # until someone finds this setting and changes it by hand. Every
        # other app in the suite already called open_gamepad() with no
        # forced backend (equivalent to "auto"); this just brings the
        # Launcher's default in line with them.
        "input_backend": "auto",
        # Open folder paths in Meridian Explorer instead of Windows
        # Explorer (suite-internal routing; system-wide handling is the
        # separate MeridianExplorerShellIntegration.bat)
        "route_folders_to_meridian_explorer": False,
        # List icon size: small (the classic 36px) | medium | large | xl,
        # each 2x the previous. Row heights grow to fit — pure frontend.
        "icon_size": "small",
        "recent_games": [],  # [{"path": ..., "name": ...}], most-recent-first, capped at 5
        "display_type": {"games": "gallery"},  # per-section-id: "list" | "gallery"; any id not present defaults to "list"
        "desktop_section_enabled": False,  # Desktop: always first in the list when on, off by default
        "explorer_section_enabled": False,  # Explorer: right after Desktop, off by default
        "browser_section_enabled": False,  # Browser: right after Explorer, off by default
        "load_subfolders": True,
        "video_fullscreen": False,
        "battery_indicator": True,
        # Off by default: force borderless-fullscreen on whatever window an
        # .exe opens, for apps that ignore the normal "start maximized"
        # request or only appear maximized with chrome still showing. See
        # fullscreen_helper.py.
        "fullscreen_helper_enabled": False,
        # when a song ends, load a random one instead of the next in list order
        "auto_shuffle_songs": True,
        "music_sort_mode": "title_asc",  # title_asc/title_desc/artist_asc/artist_desc/date_desc/random
        "play_random_song_on_startup": False,
        # CyberRadial theme: shown in the subfolder bar for sections that
        # don't have real subfolder content of their own (see
        # setSubfolderNavHidden() in app.js). None = the bundled default
        # (frontend/assets/subfolder_filler.gif).
        "subfolder_filler_gif": None,
        # Generic scannable settings for plugins/plug-ons/drop-in themes -
        # see addon_settings.py. {"<folder-name>": {"<key>": <value>}}
        "addon_settings": {},
        # Controller Bridge (see xinput_to_keyboard.py): per-item, keyed
        # by exe path - never a global toggle, see
        # _start_controller_bridge_for_path's docstring in main.py for why.
        "controller_bridge_items": [],
        "controller_bridge_mapping_path": None,
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
            _migrate_theme_media(merged)
            return merged
        except Exception:
            pass
    s = default_settings()
    save_settings(s)
    return s


def _migrate_theme_media(m):
    """Fold the old single background/overlay values into the per-theme
    dicts under the dawning_horizon slot, once, so existing users keep
    their chosen image on their current theme."""
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
