"""Meridian Launcher plugin system.

A "plugin" is a folder under Plugins/ containing:
  - plugin.json   {"id": "start", "label": "Start", "version": "1.0"}
  - backend.py    exposes list_items() and activate_item(item_id)

Plugins are auto-discovered on startup and appended as hideable custom
sections after the last manually-added custom section. Each plugin gets
its own settings entry (visible: bool, default False) persisted in
settings.json under "plugins".

A plugin's backend.py is loaded as an isolated module (not merged into
Meridian Launcher's own namespace), so plugin code stays in its own
source files and never becomes part of the main program.
"""

import importlib.util
import json
import sys
from pathlib import Path

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
    return {"id": pid, "label": label, "path": str(folder)}


def scan_plugins():
    """Returns a list of {"id", "label", "path"} for every valid plugin
    folder found under Plugins/, in directory-listing order (stable enough
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
