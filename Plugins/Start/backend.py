"""Meridian Launcher plugin: "Start"

Pulls the Windows Start Menu program folders (both the per-user and
all-users trees) into a flat, clickable list, with a "Run..." entry
pinned at the top that opens the Windows Run dialog.

This is a plain file-list/launcher plugin: it uses Meridian Launcher's
normal list navigation (up/down + A to launch), so it needs NO special
control hand-off like Meridian FileBrowse/NetBrowse do.
"""

import os
import subprocess
from pathlib import Path

# GUID for the Run dialog's shell namespace item — the standard way to
# open it from the command line without simulating the Win+R hotkey.
RUN_DIALOG_SHELL_ITEM = "shell:::{2559a1f3-21d7-11d4-bdaf-00c04f60b9f0}"

_item_cache = {}  # item_id -> absolute path, or None for the Run... entry


def _start_menu_folders():
    folders = []
    appdata = os.environ.get("APPDATA")
    if appdata:
        folders.append(Path(appdata) / "Microsoft" / "Windows" / "Start Menu" / "Programs")
    programdata = os.environ.get("PROGRAMDATA")
    if programdata:
        folders.append(Path(programdata) / "Microsoft" / "Windows" / "Start Menu" / "Programs")
    return [f for f in folders if f.is_dir()]


def list_items():
    global _item_cache
    _item_cache = {}
    items = [{"id": "run_dialog", "label": "Run...", "icon": "run"}]
    _item_cache["run_dialog"] = None

    seen_names = set()
    shortcuts = []
    for root in _start_menu_folders():
        for path in root.rglob("*.lnk"):
            name = path.stem
            key = name.lower()
            if key in seen_names:
                continue
            seen_names.add(key)
            shortcuts.append((name, path))

    shortcuts.sort(key=lambda t: t[0].lower())
    for i, (name, path) in enumerate(shortcuts):
        item_id = f"shortcut_{i}"
        _item_cache[item_id] = str(path)
        items.append({"id": item_id, "label": name, "icon": "app"})

    return items


def activate_item(item_id):
    if item_id not in _item_cache:
        # cache may be stale (e.g. plugin section reloaded); rebuild once.
        list_items()
    if item_id not in _item_cache:
        return {"ok": False, "error": "Item not found."}

    if item_id == "run_dialog":
        try:
            subprocess.Popen(["explorer.exe", RUN_DIALOG_SHELL_ITEM])
            return {"ok": True, "error": None}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    path = _item_cache[item_id]
    if not path or not os.path.exists(path):
        return {"ok": False, "error": "Shortcut target no longer exists."}
    try:
        os.startfile(path)
        return {"ok": True, "error": None}
    except Exception as e:
        return {"ok": False, "error": str(e)}
