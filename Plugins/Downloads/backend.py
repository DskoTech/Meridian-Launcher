"""Meridian Launcher plugin: "Downloads"

Fixed to the Windows user's actual Downloads folder (resolved via the
proper SHGetKnownFolderPath API, not just assuming ~/Downloads - Windows
lets Downloads be relocated to another drive/folder, and guessing wrong
would silently show an empty/wrong folder). Top-level only: no
subfolder recursion, matching "subfolder load mode off" - Downloads is
usually flat anyway, and recursing into it would risk pulling in
whatever nested folders installers/zip extractions left behind.

This is a plain list-type plugin (name + generic icon per item, no
thumbnail grid - the plugin system's list type doesn't support that,
unlike the native Photos/Videos/Music sections), functioning the same
way as those do conceptually: browse a fixed folder, open an item with
its default handler.
"""

import ctypes
import os
from pathlib import Path

# Well-known FOLDERID_Downloads GUID - Downloads has no classic CSIDL_*
# constant (it didn't exist in the original Shell folder scheme), so it
# has to be resolved via the newer SHGetKnownFolderPath API specifically.
_FOLDERID_DOWNLOADS = "{374DE290-123F-4565-9164-39C4925E467B}"

_PHOTO_EXT = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"}
_VIDEO_EXT = {".mp4", ".mkv", ".avi", ".mov", ".wmv", ".webm", ".m4v"}
_MUSIC_EXT = {".mp3", ".flac", ".wav", ".m4a", ".ogg", ".wma", ".aac"}
_ARCHIVE_EXT = {".zip", ".rar", ".7z", ".tar", ".gz"}
_INSTALLER_EXT = {".exe", ".msi"}
_DOC_EXT = {".pdf", ".doc", ".docx", ".txt", ".xls", ".xlsx", ".ppt", ".pptx"}

_item_cache = {}  # item_id -> absolute path


class _GUID(ctypes.Structure):
    _fields_ = [
        ("Data1", ctypes.c_ulong), ("Data2", ctypes.c_ushort), ("Data3", ctypes.c_ushort),
        ("Data4", ctypes.c_ubyte * 8),
    ]


def _guid_from_string(guid_str):
    import uuid
    u = uuid.UUID(guid_str)
    g = _GUID()
    g.Data1, g.Data2, g.Data3 = u.time_low, u.time_mid, u.time_hi_version
    g.Data4 = (ctypes.c_ubyte * 8)(*u.bytes[8:])
    return g


def _downloads_folder():
    try:
        guid = _guid_from_string(_FOLDERID_DOWNLOADS)
        path_ptr = ctypes.c_wchar_p()
        result = ctypes.windll.shell32.SHGetKnownFolderPath(
            ctypes.byref(guid), 0, None, ctypes.byref(path_ptr)
        )
        if result == 0 and path_ptr.value:
            path = path_ptr.value
            ctypes.windll.ole32.CoTaskMemFree(path_ptr)
            if os.path.isdir(path):
                return path
    except Exception:
        pass
    # Fallback: the conventional location, if the API call above failed
    # for any reason (e.g. running somewhere the shell32 call behaves
    # unexpectedly) - right the overwhelming majority of the time anyway.
    fallback = str(Path.home() / "Downloads")
    return fallback if os.path.isdir(fallback) else None


def _icon_for(ext):
    if ext in _PHOTO_EXT:
        return "photos"
    if ext in _VIDEO_EXT:
        return "videos"
    if ext in _MUSIC_EXT:
        return "music"
    if ext in _ARCHIVE_EXT:
        return "archive"
    if ext in _INSTALLER_EXT:
        return "apps"
    if ext in _DOC_EXT:
        return "document"
    return "generic"


def _format_size(num_bytes):
    for unit in ("B", "KB", "MB", "GB"):
        if num_bytes < 1024 or unit == "GB":
            return f"{num_bytes:.0f} {unit}" if unit == "B" else f"{num_bytes:.1f} {unit}"
        num_bytes /= 1024
    return f"{num_bytes:.1f} GB"


def list_items():
    global _item_cache
    _item_cache = {}
    folder = _downloads_folder()
    if not folder:
        return [{"id": "no_folder", "label": "Couldn't find the Downloads folder.", "icon": "generic"}]

    entries = []
    try:
        with os.scandir(folder) as it:
            for entry in it:
                if entry.name.startswith("."):
                    continue
                try:
                    if entry.is_dir():
                        continue  # top-level only - no subfolder recursion
                    stat = entry.stat()
                except OSError:
                    continue
                entries.append((entry.path, entry.name, stat.st_mtime, stat.st_size))
    except OSError:
        return [{"id": "no_folder", "label": "Couldn't read the Downloads folder.", "icon": "generic"}]

    # Most recent downloads first - the natural way anyone actually wants
    # to browse this particular folder.
    entries.sort(key=lambda e: e[2], reverse=True)

    items = []
    for i, (path, name, _mtime, size) in enumerate(entries):
        ext = os.path.splitext(name)[1].lower()
        item_id = f"dl_{i}"
        _item_cache[item_id] = path
        items.append({
            "id": item_id,
            "label": f"{name} ({_format_size(size)})",
            "icon": _icon_for(ext),
            "path": path,
        })
    if not items:
        items.append({"id": "empty", "label": "Nothing in Downloads right now.", "icon": "generic"})
    return items


def activate_item(item_id):
    if item_id in ("no_folder", "empty"):
        return {"ok": True, "error": None}
    if item_id not in _item_cache:
        list_items()
    if item_id not in _item_cache:
        return {"ok": False, "error": "Item not found."}
    path = _item_cache[item_id]
    if not path or not os.path.exists(path):
        return {"ok": False, "error": "That file no longer exists."}
    try:
        os.startfile(path)
        return {"ok": True, "error": None}
    except Exception as e:
        return {"ok": False, "error": str(e)}
