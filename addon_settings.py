"""Addon Settings - a generic, scannable settings subsystem for anything
that isn't built into Meridian Launcher itself: plugins, plug-ons
("addon"-type plugins - see plugin_manager.py), and drop-in custom
themes (themes/ folder - see user_themes.py). Backs Settings > Addon
Settings.

WHY THIS EXISTS
-----------------
Before this, a theme or plugin wanting its own configurable setting (a
gallery grid size, a custom filler image, anything) had nowhere
principled to put it - the only option was hardcoding a one-off Settings
block directly into app.js for that specific theme/plugin, which doesn't
scale and leaves no clean way to remove that theme/plugin later without
also hunting down every place its Settings block got wired in. This
subsystem is the fix: any Plugins/<name>/ or themes/<name>/ folder can
drop a settings.json describing its own settings, and Settings > Addon
Settings discovers and renders them generically - no app.js changes
needed for a new plugin/theme's settings to show up.

SCHEMA (settings.json, next to plugin.json or theme.json)
-------------------------------------------------------------
{
  "title": "My Plugin",                 (optional - defaults to the folder name)
  "fields": [
    {"key": "some_toggle", "label": "Enable Foo", "type": "toggle", "default": true},
    {"key": "some_choice", "label": "Mode", "type": "choice",
     "choices": [["a", "Option A"], ["b", "Option B"]], "default": "a"},
    {"key": "some_file", "label": "Custom Image", "type": "file",
     "accept": "Images (*.png;*.jpg;*.jpeg;*.gif;*.webp)", "default": null},
    {"key": "some_text", "label": "Custom Label", "type": "text", "default": ""}
  ]
}

Four field types: "toggle" (bool), "choice" (one of a fixed list,
cycled), "file" (native file picker, stores the chosen absolute path),
"text" (free-form string, edited via the on-screen keyboard).

Values are namespaced by folder name and persisted in SETTINGS under
"addon_settings": {"<folder-name>": {"<key>": <value>}} - completely
separate from any of that plugin/theme's OWN files, so nothing here
ever needs write access to a Plugins/ or themes/ folder.

A plugin's own backend.py, or a theme's own CSS (via a small bridge -
see get_addon_setting_value below, callable the same way from either
side) can read these values back out at runtime; this module only
handles the scanning/schema/storage side, not how a consumer chooses to
use its own values.
"""

import json
from pathlib import Path


def _scan_settings_json(folder: Path, source, manifest_id, manifest_label):
    settings_path = folder / "settings.json"
    if not settings_path.exists():
        return None
    try:
        data = json.loads(settings_path.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"Addon Settings: couldn't parse {settings_path}: {e}")
        return None
    fields = data.get("fields")
    if not isinstance(fields, list) or not fields:
        return None
    valid_fields = []
    for f in fields:
        if not isinstance(f, dict) or "key" not in f or "type" not in f:
            continue
        if f["type"] not in ("toggle", "choice", "file", "text"):
            continue
        if f["type"] == "choice" and not f.get("choices"):
            continue
        valid_fields.append(f)
    if not valid_fields:
        return None
    return {
        "id": manifest_id,
        "source": source,  # "plugin" or "theme"
        "title": data.get("title") or manifest_label,
        "fields": valid_fields,
    }


def scan_groups(base_dir: Path):
    """Returns [{"id", "source", "title", "fields": [...]}] for every
    Plugins/<name>/settings.json and themes/<name>/settings.json found -
    each folder gets checked independently of whether its plugin.json/
    theme.json otherwise validates, so a settings.json alone is enough
    to show up here."""
    groups = []

    plugins_dir = base_dir / "Plugins"
    if plugins_dir.is_dir():
        for folder in sorted(plugins_dir.iterdir()):
            if not folder.is_dir():
                continue
            manifest_id = folder.name
            manifest_label = folder.name
            manifest_path = folder / "plugin.json"
            if manifest_path.exists():
                try:
                    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                    manifest_id = manifest.get("id") or manifest_id
                    manifest_label = manifest.get("label") or manifest_label
                except Exception:
                    pass
            group = _scan_settings_json(folder, "plugin", manifest_id, manifest_label)
            if group:
                groups.append(group)

    themes_dir = base_dir / "themes"
    if themes_dir.is_dir():
        for entry in sorted(themes_dir.iterdir()):
            folder = entry if entry.is_dir() else None
            if folder is None:
                continue  # single-file (.css-only) drop-in themes can't ship a settings.json
            manifest_id = folder.name
            manifest_label = folder.name
            manifest_path = folder / "theme.json"
            if manifest_path.exists():
                try:
                    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                    manifest_label = manifest.get("name") or manifest_label
                except Exception:
                    pass
            group = _scan_settings_json(folder, "theme", manifest_id, manifest_label)
            if group:
                groups.append(group)

    return groups


def get_all_values(settings_dict, namespace_id):
    return dict(settings_dict.get("addon_settings", {}).get(namespace_id, {}))


def get_value(settings_dict, namespace_id, key, default=None):
    return settings_dict.get("addon_settings", {}).get(namespace_id, {}).get(key, default)


def set_value(settings_dict, namespace_id, key, value):
    settings_dict.setdefault("addon_settings", {})
    settings_dict["addon_settings"].setdefault(namespace_id, {})
    settings_dict["addon_settings"][namespace_id][key] = value
    return settings_dict
