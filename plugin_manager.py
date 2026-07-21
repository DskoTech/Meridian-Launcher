"""Meridian Launcher plugin system.

A "plugin" is a folder under Plugins/ containing a plugin.json manifest,
plus (for "list" plugins) a backend.py. Four plugin types:

  - "list" (default): plugin.json + backend.py exposing list_items() and
    activate_item(item_id) — a plain data-driven list, navigated the same
    way as any built-in section (see Plugins/Start/ for an example).

  - "webapp": plugin.json only, with a "url" field. Boxed into a Meridian
    NetBrowse instance pointed at that URL when the section is opened —
    the same embedded-browser-in-a-box mechanism the built-in Browser
    section uses, just permanently pinned to one site instead of
    following internally-launched links. Gets its own dedicated section
    in the Sections bar.

  - "option": same boxed-NetBrowse mechanism as "webapp" (needs a "url"
    field too), but does NOT get its own section — instead it shows up as
    a list entry inside an existing section named by its "section" field
    (e.g. "chat"). Multiple option plugins targeting the same section id
    all appear together as that section's list. Used for the Telegram/
    Discord/Messenger/Snapchat/Phone Link plugins, which all show up
    together as entries in the "Chat" section rather than five separate
    sections.

  - "addon" ("plug-ons"): same boxed mechanism as "option" (needs "url"
    and "section"), but "section" must name a BUILT-IN section (music,
    photos, videos, apps, games, emulators, explorer, browser, desktop,
    web, system — anything that isn't itself a plugin/custom section);
    see BUILTIN_SECTION_IDS. Renders as one more entry in that section's
    list, positioned after the section's own built-in entries but before
    any user-added custom entries (e.g. Web section's saved shortcuts) -
    see main.py's list_section_options for where that ordering is
    applied. Two things set an addon apart from a plain "option" plugin:

      - It's auto-disabled (excluded from list_section_options, even if
        its own "visible" flag is on) whenever its target section is
        itself hidden — there'd be nowhere for it to appear.
      - It can carry layout preferences applied while its boxed window is
        open: "window_position" (one of "default", "centered",
        "left_edge_to_right_edge", "left_half", "right_half") and
        show_subfolder/show_thumbnail/show_clock/show_battery/
        show_taskbar (booleans, default true) to hide chrome the boxed
        program doesn't need room for. See ADDON_LAYOUT_DEFAULTS below
        and embeddedBoxGeometry()/applyAddonLayout() in app.js for how
        those get used. The taskbar is the one exception even when
        show_taskbar is false: pressing X still shows it on demand,
        drawn above the boxed window rather than pushing it - see
        applyAddonLayout()'s comment.

    An examples/plugon_generator.py script scaffolds these
    interactively; "webapp"-style (open a URL) is the only kind it
    generates today, since it's the only addon behavior implemented so
    far - more addon behaviors (e.g. boxing an arbitrary outside .exe
    that draws into the options/item window rather than a URL) are meant
    to slot in the same way as this one does, once built.

Plugins are auto-discovered on startup. "list"/"webapp" plugins are
appended as hideable sections after the last manually-added custom
section; "option"/"addon" plugins are hideable list entries within
whichever section their "section" field names. Each plugin gets its own
settings entry (visible: bool, default False) persisted in settings.json
under "plugins" — this is shared across all four types, so a plug-on's
enable/disable toggle lives in the same Settings > Plugins list as every
other plugin, not a separate UI.

A "list" plugin's backend.py is loaded as an isolated module (not merged
into Meridian Launcher's own namespace), so plugin code stays in its own
source files and never becomes part of the main program.
"""

import importlib.util
import json
import sys
from pathlib import Path

# Frozen-aware: when compiled with PyInstaller, __file__ resolves into
# PyInstaller's own temp extraction folder (sys._MEIPASS et al), NOT the
# real folder MeridianLauncher.exe actually sits in on disk — using it
# directly here was why the compiled build never found a real Plugins/
# folder placed next to the exe. sys.executable is the actual exe path in
# a frozen build, matching main.py's own BASE_DIR logic exactly.
if getattr(sys, "frozen", False):
    BASE_DIR = Path(sys.executable).resolve().parent
else:
    BASE_DIR = Path(__file__).resolve().parent
PLUGINS_DIR = BASE_DIR / "Plugins"

_loaded_backends = {}  # plugin_id -> module

# Built-in sections a plug-on ("addon" type) is allowed to target — the
# Sections bar's own fixed entries, not anything a plugin (or the user's
# own custom sections) added. Keep in sync with the Sections bar's
# built-in id list in frontend/app.js.
BUILTIN_SECTION_IDS = {
    "music", "photos", "videos", "apps", "games", "emulators", "streaming",
    "explorer", "browser", "desktop", "web", "system", "chat",
}

# window_position choices a plug-on's plugin.json can set. "default" is
# whatever embeddedBoxGeometry() already computes for a plain boxed
# section/option (full list-frame box). The others are presets computed
# the same content-area-relative way (see applyAddonLayout() in app.js),
# so they're automatically clipped to start after the Sections bar/hub
# exactly like every other boxed window already is in every theme.
ADDON_WINDOW_POSITIONS = {
    "default", "centered", "left_edge_to_right_edge", "left_half", "right_half",
}

ADDON_LAYOUT_DEFAULTS = {
    "window_position": "default",
    "show_subfolder": True,
    "show_thumbnail": True,
    "show_clock": True,
    "show_battery": True,
    "show_taskbar": True,
    "show_music_player": True,
}


def _plugin_json(folder: Path):
    manifest_path = folder / "plugin.json"
    if not manifest_path.exists():
        return None
    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception:
        return None
    pid = data.get("id") or folder.name
    label = data.get("label") or folder.name
    ptype = data.get("type") or "list"
    info = {"id": pid, "label": label, "path": str(folder), "type": ptype}
    if ptype in ("webapp", "option", "addon"):
        info["url"] = data.get("url", "")
    if ptype == "option":
        info["section"] = data.get("section") or "chat"
    if ptype == "addon":
        section = data.get("section") or ""
        if section not in BUILTIN_SECTION_IDS:
            # Malformed/out-of-date manifest (targets a plugin/custom
            # section, or omits "section" entirely) - drop it rather than
            # showing a plug-on that can never actually appear anywhere.
            return None
        info["section"] = section
        info["option"] = data.get("option") or label
        layout = dict(ADDON_LAYOUT_DEFAULTS)
        for key in layout:
            if key in data:
                layout[key] = data[key]
        if layout["window_position"] not in ADDON_WINDOW_POSITIONS:
            layout["window_position"] = "default"
        info["layout"] = layout
    return info


def scan_plugins():
    """Returns a list of plugin info dicts for every valid plugin folder
    found under Plugins/, in directory-listing order (stable enough
    across runs on the same machine/filesystem)."""
    PLUGINS_DIR.mkdir(parents=True, exist_ok=True)
    found = []
    for folder in sorted(PLUGINS_DIR.iterdir()):
        if not folder.is_dir():
            continue
        info = _plugin_json(folder)
        if info:
            found.append(info)
    return found


def get_plugin_url(plugin_id):
    """For "webapp"/"option"/"addon" plugins: the fixed URL they're boxed
    to. Empty string if the plugin has no url set."""
    for info in scan_plugins():
        if info["id"] == plugin_id:
            return info.get("url", "")
    return ""


def _backend_path(plugin_id):
    for info in scan_plugins():
        if info["id"] == plugin_id:
            return Path(info["path"]) / "backend.py"
    return None


def _load_backend(plugin_id):
    if plugin_id in _loaded_backends:
        return _loaded_backends[plugin_id]
    path = _backend_path(plugin_id)
    if not path or not path.exists():
        return None
    mod_name = f"meridian_plugin_{plugin_id}"
    spec = importlib.util.spec_from_file_location(mod_name, path)
    module = importlib.util.module_from_spec(spec)
    try:
        sys.modules[mod_name] = module
        spec.loader.exec_module(module)
    except Exception as e:
        print(f"Plugin '{plugin_id}' failed to load: {e}")
        sys.modules.pop(mod_name, None)
        return None
    _loaded_backends[plugin_id] = module
    return module


def unload_backend(plugin_id):
    """Drop a cached plugin backend module (e.g. after a rescan) so a
    future call reloads fresh code from disk."""
    mod = _loaded_backends.pop(plugin_id, None)
    if mod:
        sys.modules.pop(mod.__name__, None)


def list_items(plugin_id):
    module = _load_backend(plugin_id)
    if module is None or not hasattr(module, "list_items"):
        return []
    try:
        return module.list_items()
    except Exception as e:
        print(f"Plugin '{plugin_id}' list_items() failed: {e}")
        return []


def activate_item(plugin_id, item_id):
    module = _load_backend(plugin_id)
    if module is None or not hasattr(module, "activate_item"):
        return {"ok": False, "error": "Plugin has no activate_item()."}
    try:
        return module.activate_item(item_id)
    except Exception as e:
        return {"ok": False, "error": str(e)}


def delete_item(plugin_id, item_id):
    """Optional hook: a "list"-type plugin can define delete_item(item_id)
    to support Meridian Launcher's Start-menu Delete option (send-to-
    Recycle-Bin) for its own real files, the same way the built-in
    Desktop section does for its own - see Plugins/Start/backend.py for
    the reference implementation. Plugins that don't define it (most
    won't - it's only meaningful for a plugin whose items are real
    files) just aren't offered the option at all."""
    module = _load_backend(plugin_id)
    if module is None or not hasattr(module, "delete_item"):
        return {"ok": False, "error": "This plugin doesn't support deleting items."}
    try:
        return module.delete_item(item_id)
    except Exception as e:
        return {"ok": False, "error": str(e)}
