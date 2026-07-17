"""Meridian Launcher plugin system.

A "plugin" is a folder under Plugins/ containing a plugin.json manifest,
plus (for "list" plugins) a backend.py. Three plugin types:

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

Plugins are auto-discovered on startup. "list"/"webapp" plugins are
appended as hideable sections after the last manually-added custom
section; "option" plugins are hideable list entries within whichever
section their "section" field names. Each plugin gets its own settings
entry (visible: bool, default False) persisted in settings.json under
"plugins".

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
    if ptype in ("webapp", "option"):
        info["url"] = data.get("url", "")
    if ptype == "option":
        info["section"] = data.get("section") or "chat"
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
    """For "webapp"/"option" plugins: the fixed URL they're boxed to.
    Empty string if the plugin has no url set."""
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
