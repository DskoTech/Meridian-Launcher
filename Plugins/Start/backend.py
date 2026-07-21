"""Meridian Launcher plugin: "Start"

Pulls the Windows Start Menu program folders (both the per-user and
all-users trees) into a flat, clickable list, with a "Run..." entry
pinned at the top that opens the Windows Run dialog.

This is a plain file-list/launcher plugin: it uses Meridian Launcher's
normal list navigation (up/down + A to launch), so it needs NO special
control hand-off like Meridian FileBrowse/NetBrowse do.

Each shortcut item also exposes its real .lnk file path (item["path"]) -
used by Meridian Launcher's Start-menu "Delete" option (see
delete_item() below and plugin_manager.delete_item()), the same
send-to-Recycle-Bin action the Desktop section offers for its own real
files. "run_dialog" has no path (it isn't a file) and is never eligible.
"""

import os
import subprocess
from pathlib import Path

# BASE_DIR (main.py's own folder) needs to be importable for
# system_actions - plugin backends run with the main process's sys.path,
# which already includes it (that's where main.py itself lives), so this
# works the same way any of main.py's own top-level imports do.
import system_actions

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
        items.append({"id": item_id, "label": name, "icon": "app", "path": str(path)})

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


def delete_item(item_id):
    """Sends the shortcut's .lnk file to the Recycle Bin - removes it
    from the Windows Start Menu (and this list), not the program itself.
    Scoped to only ever delete something actually inside one of the
    Start Menu Programs folders, same safety pattern as the Desktop
    section's own delete."""
    if item_id not in _item_cache:
        list_items()
    path = _item_cache.get(item_id)
    if not path:
        return {"ok": False, "error": "That item isn't a real file (e.g. Run...)."}
    allowed_roots = [os.path.normcase(os.path.abspath(str(f))) for f in _start_menu_folders()]
    target = os.path.normcase(os.path.abspath(path))
    if not any(target.startswith(root) for root in allowed_roots):
        return {"ok": False, "error": "Refusing to delete something outside the Start Menu folders."}
    ok, err = system_actions.delete_to_recycle_bin(path)
    return {"ok": ok, "error": err}
