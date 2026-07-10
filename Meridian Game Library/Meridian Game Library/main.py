"""
Meridian Game Library — a Windows game library front-end.

Sections: Music, Photos, Videos, Apps, Games, Emulators, Chat, Streaming,
Web, Files, System, Macros, plus user-defined custom sections. Navigable by
keyboard, mouse, or game controller (XInput).
"""

import ctypes
import hashlib
import json
import mimetypes
import os
import shutil
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse, parse_qs

import webview

# pywebview defaults to opening any navigation it considers "external"
# (including cross-subdomain hops) in the user's system browser instead of
# inside the embedded window. GOG's and Epic's login flows both bounce
# across several subdomains as part of a normal OAuth redirect chain
# (e.g. login.gog.com -> auth.gog.com -> embed.gog.com), so with the
# default left on, the login popup gets ejected to the system browser
# mid-flow — the popup's own page-load watcher then never sees the final
# redirect URL, and login silently goes nowhere. This must be set before
# any window is created.
webview.settings["OPEN_EXTERNAL_LINKS_IN_BROWSER"] = False

import store
import system_actions
import playnite_import
import playnite_sync
from controller_input import ControllerListener

try:
    import win32gui
    import win32con
    import win32ui
    import win32api
except ImportError:
    win32gui = None
    win32con = None
    win32ui = None
    win32api = None

BASE_DIR = store.BASE_DIR
APP_TITLE = "Meridian Game Library"

MUSIC_EXT = {".mp3", ".flac", ".wav", ".m4a", ".ogg", ".wma", ".aac"}
PHOTO_EXT = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"}
VIDEO_EXT = {".mp4", ".mkv", ".avi", ".mov", ".wmv", ".webm", ".m4v"}
IMAGE_FILE_TYPES = ("Image Files (*.png;*.jpg;*.jpeg;*.bmp;*.webp)",)
VIDEO_FILE_TYPES = ("Video Files (*.mp4;*.webm;*.mov;*.mkv;*.avi)",)
EXE_FILE_TYPES = ("Executable Files (*.exe)",)
BAT_FILE_TYPES = ("Batch Files (*.bat)",)

SETTINGS = store.load_settings()
store.ensure_controls_files()


# --------------------------------------------------------------------------
# Local streaming server (range-aware, used for music/video/photo/overlay/bg)
# --------------------------------------------------------------------------

TOKEN_MAP = {}


def token_for(path: str) -> str:
    h = hashlib.sha1(str(path).encode("utf-8")).hexdigest()
    TOKEN_MAP[h] = path
    return h


class MediaHandler(BaseHTTPRequestHandler):
    def log_message(self, *_a):
        pass

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path != "/media":
            self.send_error(404)
            return
        qs = parse_qs(parsed.query)
        token = qs.get("t", [None])[0]
        path = TOKEN_MAP.get(token)
        if not path or not os.path.isfile(path):
            self.send_error(404)
            return

        file_size = os.path.getsize(path)
        mime = mimetypes.guess_type(path)[0] or "application/octet-stream"
        range_header = self.headers.get("Range")

        if range_header:
            try:
                _, rng = range_header.split("=")
                start_s, end_s = rng.split("-")
                start = int(start_s)
                end = int(end_s) if end_s else file_size - 1
            except Exception:
                start, end = 0, file_size - 1
            end = min(end, file_size - 1)
            length = end - start + 1
            self.send_response(206)
            self.send_header("Content-Range", f"bytes {start}-{end}/{file_size}")
            self.send_header("Accept-Ranges", "bytes")
            self.send_header("Content-Length", str(length))
            self.send_header("Content-Type", mime)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            with open(path, "rb") as f:
                f.seek(start)
                remaining = length
                while remaining > 0:
                    chunk = f.read(min(65536, remaining))
                    if not chunk:
                        break
                    try:
                        self.wfile.write(chunk)
                    except (BrokenPipeError, ConnectionResetError):
                        return
                    remaining -= len(chunk)
        else:
            self.send_response(200)
            self.send_header("Accept-Ranges", "bytes")
            self.send_header("Content-Length", str(file_size))
            self.send_header("Content-Type", mime)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            with open(path, "rb") as f:
                try:
                    shutil.copyfileobj(f, self.wfile)
                except (BrokenPipeError, ConnectionResetError):
                    return


def start_media_server():
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), MediaHandler)
    port = httpd.server_address[1]
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return port


MEDIA_PORT = start_media_server()


def media_url(path):
    if not path:
        return None
    return f"http://127.0.0.1:{MEDIA_PORT}/media?t={token_for(str(path))}"


# --------------------------------------------------------------------------
# Thumbnails & metadata (music / photos / videos)
# --------------------------------------------------------------------------

CACHE_DIR = BASE_DIR / ".cache"
CACHE_DIR.mkdir(exist_ok=True)


def _cache_path(key):
    return CACHE_DIR / (hashlib.sha1(key.encode("utf-8")).hexdigest() + ".jpg")


def ffmpeg_available():
    return shutil.which("ffmpeg") is not None


def ffprobe_available():
    return shutil.which("ffprobe") is not None


def get_video_thumb(path):
    out = _cache_path("vid:" + path)
    if out.exists():
        return str(out)
    if not ffmpeg_available():
        return None
    try:
        subprocess.run(
            ["ffmpeg", "-y", "-ss", "00:00:03", "-i", path,
             "-frames:v", "1", "-vf", "scale=320:-1", str(out)],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=15,
        )
        return str(out) if out.exists() else None
    except Exception:
        return None


def get_music_thumb(path):
    out = _cache_path("aud:" + path)
    if out.exists():
        return str(out)
    try:
        from mutagen import File as MutagenFile
        f = MutagenFile(path)
        if f is None or not getattr(f, "tags", None):
            return None
        art_bytes = None
        for key in f.tags.keys():
            if str(key).startswith("APIC"):
                art_bytes = f.tags[key].data
                break
        if art_bytes is None and "covr" in f.tags:
            art_bytes = bytes(f.tags["covr"][0])
        if art_bytes:
            out.write_bytes(art_bytes)
            return str(out)
    except Exception:
        pass
    return None


def get_photo_thumb(path):
    out = _cache_path("img:" + path)
    if out.exists():
        return str(out)
    try:
        from PIL import Image, ImageOps
        im = Image.open(path)
        im = ImageOps.exif_transpose(im)
        im.thumbnail((360, 360))
        im.convert("RGB").save(out, "JPEG", quality=82)
        return str(out)
    except Exception:
        return None


def get_file_icon(path):
    """Extract the icon Windows Explorer would show for this file (.exe, .bat,
    etc.) and cache it as a PNG. Returns None if extraction isn't possible
    (e.g. running outside Windows, or pywin32 missing)."""
    out = _cache_path("icon:" + path)
    if out.exists():
        return str(out)
    if win32gui is None or win32ui is None or win32api is None:
        return None
    if not os.path.isfile(path):
        return None
    large, small = [], []
    try:
        from PIL import Image

        large, small = win32gui.ExtractIconEx(path, 0)
        handles = large or small
        if not handles:
            return None
        hicon = handles[0]

        ico_x = win32api.GetSystemMetrics(win32con.SM_CXICON)
        ico_y = win32api.GetSystemMetrics(win32con.SM_CYICON)

        hdc_screen = win32gui.GetDC(0)
        hdc = win32ui.CreateDCFromHandle(hdc_screen)
        hdc_mem = hdc.CreateCompatibleDC()

        hbmp = win32ui.CreateBitmap()
        hbmp.CreateCompatibleBitmap(hdc, ico_x, ico_y)
        hdc_mem.SelectObject(hbmp)
        hdc_mem.DrawIcon((0, 0), hicon)

        bmpinfo = hbmp.GetInfo()
        bmpstr = hbmp.GetBitmapBits(True)
        img = Image.frombuffer(
            "RGBA",
            (bmpinfo["bmWidth"], bmpinfo["bmHeight"]),
            bmpstr, "raw", "BGRA", 0, 1,
        )
        img.save(out, "PNG")

        win32gui.DeleteObject(hbmp.GetHandle())
        hdc_mem.DeleteDC()
        win32gui.ReleaseDC(0, hdc_screen)
        return str(out)
    except Exception:
        return None
    finally:
        for h in set(large) | set(small):
            try:
                win32gui.DestroyIcon(h)
            except Exception:
                pass


def read_audio_meta(path):
    title, artist, album, duration = Path(path).stem, "Unknown Artist", "Unknown Album", 0
    try:
        from mutagen import File as MutagenFile
        f = MutagenFile(path, easy=True)
        if f:
            title = (f.get("title") or [title])[0]
            artist = (f.get("artist") or [artist])[0]
            album = (f.get("album") or [album])[0]
            if f.info and getattr(f.info, "length", None):
                duration = int(f.info.length)
    except Exception:
        pass
    return {"title": title, "artist": artist, "album": album, "duration": duration}


def read_video_meta(path):
    duration = 0
    if ffprobe_available():
        try:
            out = subprocess.run(
                ["ffprobe", "-v", "error", "-show_entries", "format=duration",
                 "-of", "default=noprint_wrappers=1:nokey=1", path],
                capture_output=True, text=True, timeout=10,
            )
            duration = int(float(out.stdout.strip()))
        except Exception:
            pass
    return {"title": Path(path).stem, "duration": duration}


def scan_dir(folder, extset):
    found = []
    for root, _dirs, files in os.walk(folder):
        for name in files:
            if Path(name).suffix.lower() in extset:
                found.append(str(Path(root) / name))
    return found


def _scan_flat(folder, extset):
    """Non-recursive: only files directly inside `folder`, used for manual
    subfolder browsing when Load Subfolders is disabled."""
    found = []
    try:
        with os.scandir(folder) as it:
            for entry in it:
                if entry.is_file() and Path(entry.name).suffix.lower() in extset:
                    found.append(entry.path)
    except OSError:
        pass
    return found


def _list_subfolders(folder):
    subs = []
    try:
        with os.scandir(folder) as it:
            for entry in it:
                if entry.is_dir():
                    subs.append(entry.name)
    except OSError:
        pass
    return sorted(subs, key=str.lower)


def fmt_duration(seconds):
    seconds = int(seconds or 0)
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


# --------------------------------------------------------------------------
# Index cache — avoids re-reading tags / regenerating thumbnails for files
# that haven't changed since the last scan. Thumbnails/icons already cache
# themselves to disk by content hash; this adds a second layer that skips
# even the "does the file still need X" work for anything with an unchanged
# mtime, which matters a lot once a library has thousands of files.
# --------------------------------------------------------------------------

def _index_cache_path(kind):
    return CACHE_DIR / f"index_{kind}.json"


def _load_index_cache(kind):
    p = _index_cache_path(kind)
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"files": {}, "items": {}}


def _save_index_cache(kind, cache):
    try:
        _index_cache_path(kind).write_text(json.dumps(cache), encoding="utf-8")
    except Exception:
        pass


def _build_entry(kind, path):
    """Build one library entry's metadata + thumbnail (expensive part)."""
    entry = {"path": path, "name": Path(path).name}
    thumb = None
    if kind == "music":
        entry.update(read_audio_meta(path))
        entry["durationLabel"] = fmt_duration(entry.get("duration", 0))
        thumb = get_music_thumb(path)
    elif kind == "videos":
        entry.update(read_video_meta(path))
        entry["durationLabel"] = fmt_duration(entry.get("duration", 0))
        thumb = get_video_thumb(path)
    else:
        entry["title"] = Path(path).stem
        thumb = get_photo_thumb(path)
    entry["_thumb_path"] = thumb  # raw path, not a URL — tokens are per-run, see below
    return entry


def _entries_to_response(kind, path_to_entry):
    """Turn cached/raw entries (with a stashed thumb path) into the shape
    the frontend expects, generating fresh media-server tokens every call
    since TOKEN_MAP doesn't persist across runs."""
    items = []
    for path, entry in path_to_entry.items():
        e = dict(entry)
        thumb = e.pop("_thumb_path", None)
        e["thumbUrl"] = media_url(thumb) if thumb else None
        if kind == "photos":
            e["fullUrl"] = media_url(path)
        else:
            e["url"] = media_url(path)
        items.append(e)
    items.sort(key=lambda e: e.get("title", e["name"]).lower())
    return items


# --------------------------------------------------------------------------
# Section helpers (apps/games/emulators/chat/streaming/custom/macros)
# --------------------------------------------------------------------------

def _section_store(section_id):
    """Return the mutable items dict for a fixed or custom exe-list section."""
    if section_id in SETTINGS["sections"]:
        return SETTINGS["sections"][section_id]
    for cs in SETTINGS["custom_sections"]:
        if cs["id"] == section_id:
            SETTINGS["sections"].setdefault(section_id, {"items": []})
            return SETTINGS["sections"][section_id]
    return None


def _with_icons(items):
    out = []
    for it in items:
        entry = dict(it)
        icon_path = get_file_icon(it["path"])
        entry["iconUrl"] = media_url(icon_path) if icon_path else None
        out.append(entry)
    return out


def _open_file_dialog(file_types):
    window = webview.windows[0]
    result = window.create_file_dialog(webview.OPEN_DIALOG, file_types=file_types, allow_multiple=True)
    return list(result) if result else []


# --------------------------------------------------------------------------
# JS-facing API
# --------------------------------------------------------------------------

class Api:
    # ---------------- settings / controls ----------------
    def get_settings(self):
        SETTINGS.setdefault("playnite", {"export_path": None})
        SETTINGS["playnite"]["export_available"] = playnite_import.export_file_available(SETTINGS["playnite"])
        return SETTINGS

    def get_keyboard_controls(self):
        return store.load_keyboard_controls()

    def get_controller_controls(self):
        return store.load_controller_controls()

    # ---------------- Storefronts (Steam/GOG/Epic/Luna/Other, all backed by Playnite) ----------------
    #
    # Meridian Game Library no longer talks to Steam/GOG/Epic/Amazon directly at all.
    # It reads a JSON export written by the MeridianExporter Playnite
    # extension and delegates actions back to Playnite only when it has
    # to. See playnite_import.py for the full reasoning, including why
    # launching an installed game usually bypasses Playnite entirely.

    STORE_KEYS = ("steam", "gog", "epic", "amazon", "other")

    def _playnite_settings(self):
        return SETTINGS.setdefault("playnite", {"export_path": None, "executable_path": None})

    def playnite_pick_export_file(self):
        result = webview.windows[0].create_file_dialog(
            webview.OPEN_DIALOG,
            file_types=("JSON files (*.json)", "All files (*.*)"),
        )
        return result[0] if result else None

    def playnite_set_export_path(self, path):
        self._playnite_settings()["export_path"] = path or None
        store.save_settings(SETTINGS)
        return SETTINGS

    def playnite_status(self):
        cfg = self._playnite_settings()
        available = playnite_import.export_file_available(cfg)
        summary = playnite_import.export_summary(cfg) if available else None
        return {
            "available": available,
            "export_path": playnite_import.get_export_path(cfg),
            "summary": summary,
        }

    def playnite_sync_now(self):
        """Manual 'sync now' from Settings — runs the same silent background sync as startup, but blocking so the UI can show a result."""
        return {"synced": playnite_sync.silent_sync(self._playnite_settings(), timeout=90)}

    def _store_login(self, store_key):
        # There's no real per-store "login" anymore — connection state is
        # just "does the Playnite export file exist yet". Kept as a method
        # per store so the frontend's existing login-prompt flow (built for
        # the old per-store auth) still works without changes.
        cfg = self._playnite_settings()
        if playnite_import.export_file_available(cfg):
            return {"success": True}
        return {
            "success": False,
            "error": "No Playnite export found yet — install the MeridianExporter Playnite extension and sync your library first (see Settings).",
        }

    def _entries_with_media_urls(self, entries):
        # Cover art paths from Playnite are arbitrary local files outside
        # the app's own frontend folder. Raw file:// URLs to those are
        # unreliable in pywebview's edgechromium backend (this is exactly
        # why the existing music/photos/video code already routes local
        # files through the tokenized media server instead of file:// —
        # reusing that same proven path here rather than a raw file URL).
        for entry in entries:
            if entry.get("art"):
                entry["art"] = media_url(entry["art"])
        return entries

    def _store_get_library(self, store_key):
        entries = playnite_import.get_library(store_key, self._playnite_settings())
        return {"entries": self._entries_with_media_urls(entries or [])}

    def _store_sync_library(self, store_key, force=False):
        # "Sync" is just "re-read the export file" now — no network calls,
        # so this is effectively instant. The actual freshness of the data
        # depends on when the Playnite extension last wrote the file.
        entries = playnite_import.get_library(store_key, self._playnite_settings())
        if entries is None:
            return {"error": "not_logged_in"}
        return {"entries": self._entries_with_media_urls(entries)}

    def _store_launch(self, game_id):
        playnite_import.launch_game(game_id, self._playnite_settings())

    def _store_install_or_uninstall(self, game_id):
        playnite_import.show_in_playnite(game_id)

    def steam_login(self):
        return self._store_login("steam")

    def gog_login(self):
        return self._store_login("gog")

    def epic_login(self):
        return self._store_login("epic")

    def amazon_login(self):
        return self._store_login("amazon")

    def other_login(self):
        return self._store_login("other")

    def steam_get_library(self):
        return self._store_get_library("steam")

    def gog_get_library(self):
        return self._store_get_library("gog")

    def epic_get_library(self):
        return self._store_get_library("epic")

    def amazon_get_library(self):
        return self._store_get_library("amazon")

    def other_get_library(self):
        return self._store_get_library("other")

    def steam_sync_library(self, force=False):
        return self._store_sync_library("steam", force)

    def gog_sync_library(self, force=False):
        return self._store_sync_library("gog", force)

    def epic_sync_library(self, force=False):
        return self._store_sync_library("epic", force)

    def amazon_sync_library(self, force=False):
        return self._store_sync_library("amazon", force)

    def other_sync_library(self, force=False):
        return self._store_sync_library("other", force)

    def steam_launch(self, game_id):
        self._store_launch(game_id)

    def gog_launch(self, game_id):
        self._store_launch(game_id)

    def epic_launch(self, game_id):
        self._store_launch(game_id)

    def amazon_launch(self, game_id):
        self._store_launch(game_id)

    def other_launch(self, game_id):
        self._store_launch(game_id)

    def steam_install(self, game_id):
        self._store_install_or_uninstall(game_id)

    def gog_open_download_page(self, game_id):
        self._store_install_or_uninstall(game_id)

    def epic_install(self, game_id):
        self._store_install_or_uninstall(game_id)

    def amazon_install(self, game_id):
        self._store_install_or_uninstall(game_id)

    def other_install(self, game_id):
        self._store_install_or_uninstall(game_id)

    def steam_uninstall(self, game_id):
        self._store_install_or_uninstall(game_id)

    def gog_uninstall(self, game_id):
        self._store_install_or_uninstall(game_id)

    def epic_uninstall(self, game_id):
        self._store_install_or_uninstall(game_id)

    def amazon_uninstall(self, game_id):
        self._store_install_or_uninstall(game_id)

    def other_uninstall(self, game_id):
        self._store_install_or_uninstall(game_id)

    # ---------------- media folders ----------------
    def pick_folder(self):
        result = webview.windows[0].create_file_dialog(webview.FOLDER_DIALOG)
        return result[0] if result else None

    def add_folder(self, kind, path):
        if kind in SETTINGS["folders"] and path and path not in SETTINGS["folders"][kind]:
            SETTINGS["folders"][kind].append(path)
            store.save_settings(SETTINGS)
        return SETTINGS

    def remove_folder(self, kind, path):
        if kind in SETTINGS["folders"] and path in SETTINGS["folders"][kind]:
            SETTINGS["folders"][kind].remove(path)
            store.save_settings(SETTINGS)
        return SETTINGS

    def has_ffmpeg(self):
        return ffmpeg_available()

    def scan_library(self, kind):
        extmap = {"music": MUSIC_EXT, "photos": PHOTO_EXT, "videos": VIDEO_EXT}
        if kind not in extmap:
            return []

        cache = _load_index_cache(kind)
        cached_mtimes = cache.get("files", {})
        cached_items = cache.get("items", {})

        current_mtimes = {}
        for folder in SETTINGS["folders"].get(kind, []):
            if not os.path.isdir(folder):
                continue
            for path in scan_dir(folder, extmap[kind]):
                try:
                    current_mtimes[path] = os.path.getmtime(path)
                except OSError:
                    continue

        fresh_items = {}
        for path, mtime in current_mtimes.items():
            if path in cached_items and cached_mtimes.get(path) == mtime:
                fresh_items[path] = cached_items[path]  # unchanged: skip re-reading tags/thumbnail entirely
            else:
                fresh_items[path] = _build_entry(kind, path)

        _save_index_cache(kind, {"files": current_mtimes, "items": fresh_items})
        return _entries_to_response(kind, fresh_items)

    def browse_folder(self, kind, path):
        """Non-recursive single-directory listing, used by the subfolder
        navigation sidebar when Load Subfolders is disabled."""
        extmap = {"music": MUSIC_EXT, "photos": PHOTO_EXT, "videos": VIDEO_EXT}
        if kind not in extmap or not path or not os.path.isdir(path):
            return {"path": path, "subfolders": [], "items": []}
        subfolders = _list_subfolders(path)
        entries = {p: _build_entry(kind, p) for p in _scan_flat(path, extmap[kind])}
        return {"path": path, "subfolders": subfolders, "items": _entries_to_response(kind, entries)}

    def get_root_folders(self, kind):
        return SETTINGS["folders"].get(kind, [])

    # ---------------- exe-list sections (apps/games/emulators/chat/streaming/custom) ----------------
    def list_section_items(self, section_id):
        sec = _section_store(section_id)
        return _with_icons(sec["items"]) if sec else []

    def add_exe_to_section(self, section_id):
        sec = _section_store(section_id)
        if sec is None:
            return []
        paths = _open_file_dialog(EXE_FILE_TYPES)
        for p in paths:
            if not any(it["path"] == p for it in sec["items"]):
                sec["items"].append({"path": p, "name": store.display_name(p)})
        store.save_settings(SETTINGS)
        return _with_icons(sec["items"])

    def remove_exe_from_section(self, section_id, path):
        sec = _section_store(section_id)
        if sec is None:
            return []
        sec["items"] = [it for it in sec["items"] if it["path"] != path]
        store.save_settings(SETTINGS)
        return _with_icons(sec["items"])

    def launch_exe(self, path):
        ok, err = system_actions.launch_path(path)
        return {"ok": ok, "error": err}

    # ---------------- custom sections ----------------
    def add_custom_section(self, name):
        name = (name or "").strip()
        if not name:
            return SETTINGS
        base_id = store.slugify(name)
        sid = base_id
        i = 2
        existing_ids = {cs["id"] for cs in SETTINGS["custom_sections"]} | set(SETTINGS["sections"].keys())
        while sid in existing_ids:
            sid = f"{base_id}-{i}"
            i += 1
        SETTINGS["custom_sections"].append({"id": sid, "label": name})
        SETTINGS["sections"][sid] = {"items": []}
        store.save_settings(SETTINGS)
        return SETTINGS

    def remove_custom_section(self, section_id):
        SETTINGS["custom_sections"] = [cs for cs in SETTINGS["custom_sections"] if cs["id"] != section_id]
        SETTINGS["sections"].pop(section_id, None)
        store.save_settings(SETTINGS)
        return SETTINGS

    # ---------------- macros ----------------
    def list_macro_items(self):
        builtin = [{"type": "builtin", "id": "close_others", "name": "Close all other programs"}]
        bats = _with_icons(SETTINGS["sections"]["macros"]["items"])
        for b in bats:
            b["type"] = "bat"
        return builtin + bats

    def add_bat_to_macros(self):
        paths = _open_file_dialog(BAT_FILE_TYPES)
        for p in paths:
            items = SETTINGS["sections"]["macros"]["items"]
            if not any(it["path"] == p for it in items):
                items.append({"type": "bat", "path": p, "name": store.display_name(p)})
        store.save_settings(SETTINGS)
        return self.list_macro_items()

    def remove_macro_item(self, path):
        items = SETTINGS["sections"]["macros"]["items"]
        SETTINGS["sections"]["macros"]["items"] = [it for it in items if it["path"] != path]
        store.save_settings(SETTINGS)
        return self.list_macro_items()

    def run_macro(self, macro_id):
        if macro_id == "close_others":
            whitelist = set(SETTINGS.get("macros_whitelist", []))
            whitelist.add("onscreenmenu.exe")
            whitelist.add(Path(sys.executable).name)
            return system_actions.close_all_except(whitelist)
        return {"ok": False, "error": "Unknown macro"}

    # ---------------- web / files / system ----------------
    def open_web(self):
        ok, err = system_actions.open_default_browser()
        return {"ok": ok, "error": err}

    def open_files(self):
        ok, err = system_actions.open_this_pc()
        return {"ok": ok, "error": err}

    def system_shutdown(self):
        ok, err = system_actions.shutdown()
        return {"ok": ok, "error": err}

    def system_sleep(self):
        ok, err = system_actions.sleep()
        return {"ok": ok, "error": err}

    def system_hibernate(self):
        ok, err = system_actions.hibernate()
        return {"ok": ok, "error": err}

    def system_control_panel(self):
        ok, err = system_actions.open_control_panel()
        return {"ok": ok, "error": err}

    def system_task_manager(self):
        ok, err = system_actions.open_task_manager()
        return {"ok": ok, "error": err}

    def system_recycle_bin(self):
        ok, err = system_actions.open_recycle_bin()
        return {"ok": ok, "error": err}

    def system_uninstall_apps(self):
        ok, err = system_actions.open_uninstall_apps()
        return {"ok": ok, "error": err}

    def get_battery_status(self):
        return system_actions.get_battery_status()

    # ---------------- Wi-Fi ----------------
    def wifi_scan(self):
        ok, data = system_actions.wifi_scan()
        return {"ok": ok, "networks": data if ok else [], "error": None if ok else data}

    def wifi_connect(self, ssid, password=""):
        ok, err = system_actions.wifi_connect(ssid, password)
        return {"ok": ok, "error": err}

    def wifi_disconnect(self):
        ok, err = system_actions.wifi_disconnect()
        return {"ok": ok, "error": err}

    # ---------------- Bluetooth (best-effort — see system_actions.py) ----------------
    def bluetooth_list_devices(self):
        ok, data = system_actions.bluetooth_list_devices()
        return {"ok": ok, "devices": data if ok else [], "error": None if ok else data}

    def bluetooth_connect(self, device_id):
        ok, err = system_actions.bluetooth_set_enabled(device_id, True)
        return {"ok": ok, "error": err}

    def bluetooth_disconnect(self, device_id):
        ok, err = system_actions.bluetooth_set_enabled(device_id, False)
        return {"ok": ok, "error": err}

    def open_bluetooth_settings(self):
        ok, err = system_actions.open_bluetooth_settings()
        return {"ok": ok, "error": err}

    # ---------------- Files section ----------------
    def launch_meridian_explorer(self):
        exe = BASE_DIR / "Meridian_Explorer.exe"
        if not exe.exists():
            return {"ok": False, "error": "Meridian_Explorer.exe not found in the app folder."}
        ok, err = system_actions.launch_path(str(exe))
        return {"ok": ok, "error": err}

    def quit_app(self):
        os._exit(0)

    # ---------------- appearance ----------------
    def set_background(self):
        paths = _open_file_dialog(IMAGE_FILE_TYPES)
        if paths:
            SETTINGS["background_image"] = paths[0]
            store.save_settings(SETTINGS)
        return SETTINGS

    def clear_background(self):
        SETTINGS["background_image"] = None
        store.save_settings(SETTINGS)
        return SETTINGS

    def set_overlay(self):
        paths = _open_file_dialog(IMAGE_FILE_TYPES)
        if paths:
            try:
                from PIL import Image
                im = Image.open(paths[0]).convert("RGBA")
                im.save(store.OVERLAY_FILE, "PNG")
                SETTINGS["overlay_image"] = str(store.OVERLAY_FILE)
                SETTINGS["overlay_enabled"] = True
            except Exception:
                pass
            store.save_settings(SETTINGS)
        return SETTINGS

    def set_overlay_enabled(self, enabled):
        SETTINGS["overlay_enabled"] = bool(enabled)
        store.save_settings(SETTINGS)
        return SETTINGS

    def clear_overlay(self):
        SETTINGS["overlay_image"] = None
        SETTINGS["overlay_enabled"] = False
        store.save_settings(SETTINGS)
        return SETTINGS

    def set_opening_video(self):
        paths = _open_file_dialog(VIDEO_FILE_TYPES)
        if paths:
            SETTINGS["opening_video"] = paths[0]
            store.save_settings(SETTINGS)
        return SETTINGS

    def clear_opening_video(self):
        SETTINGS["opening_video"] = None
        store.save_settings(SETTINGS)
        return SETTINGS

    def get_media_url(self, path):
        return media_url(path)

    def set_load_subfolders(self, enabled):
        SETTINGS["load_subfolders"] = bool(enabled)
        store.save_settings(SETTINGS)
        return SETTINGS

    def set_video_fullscreen(self, enabled):
        SETTINGS["video_fullscreen"] = bool(enabled)
        store.save_settings(SETTINGS)
        return SETTINGS

    def set_battery_indicator(self, enabled):
        SETTINGS["battery_indicator"] = bool(enabled)
        store.save_settings(SETTINGS)
        return SETTINGS

    def set_window_mode(self, mode):
        SETTINGS["window_mode"] = mode
        store.save_settings(SETTINGS)
        try:
            win = webview.windows[0]
            if mode == "fullscreen" and not getattr(win, "_meridian_fullscreen", False):
                win.toggle_fullscreen()
                win._meridian_fullscreen = True
            elif mode == "windowed" and getattr(win, "_meridian_fullscreen", False):
                win.toggle_fullscreen()
                win._meridian_fullscreen = False
        except Exception:
            pass
        return SETTINGS


# --------------------------------------------------------------------------
# Controller wiring
# --------------------------------------------------------------------------

def _bring_to_foreground():
    if win32gui is None:
        return
    try:
        hwnd = win32gui.FindWindow(None, APP_TITLE)
        if hwnd:
            if win32gui.IsIconic(hwnd):
                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            win32gui.SetForegroundWindow(hwnd)
    except Exception:
        pass


def _quit_via_combo():
    os._exit(0)


def _controller_action(action_name):
    try:
        webview.windows[0].evaluate_js(f"window.handleControllerInput && window.handleControllerInput('{action_name}')")
    except Exception:
        pass


def _controller_any():
    try:
        webview.windows[0].evaluate_js("window.handleControllerAny && window.handleControllerAny()")
    except Exception:
        pass


def start_controller():
    controls = store.load_controller_controls()
    listener = ControllerListener(
        controls,
        on_action=_controller_action,
        on_any=_controller_any,
        on_quit_combo=_quit_via_combo,
        on_foreground_combo=_bring_to_foreground,
    )
    listener.start()
    return listener


# --------------------------------------------------------------------------
# Boot: onscreenmenu.exe, resolution detection, window creation
# --------------------------------------------------------------------------

def launch_onscreenmenu():
    exe = BASE_DIR / "onscreenmenu.exe"
    if exe.exists():
        try:
            subprocess.Popen([str(exe)], cwd=str(BASE_DIR))
        except Exception:
            pass


def detect_screen_size():
    try:
        user32 = ctypes.windll.user32
        return user32.GetSystemMetrics(0), user32.GetSystemMetrics(1)
    except Exception:
        return 1280, 800


def main():
    launch_onscreenmenu()

    width, height = detect_screen_size()
    mode = SETTINGS.get("window_mode", "fullscreen")
    fullscreen = mode == "fullscreen"
    frameless = False

    api = Api()
    window = webview.create_window(
        APP_TITLE,
        str(BASE_DIR / "frontend" / "index.html"),
        js_api=api,
        width=width,
        height=height,
        min_size=(1024, 640),
        background_color="#05070d",
        fullscreen=fullscreen,
        frameless=frameless,
    )
    window._meridian_fullscreen = fullscreen

    # Best-effort library freshness: silently launch Playnite in the
    # background, wait for its MeridianExporter extension to rewrite the
    # export file (proof a library sync completed), then close it again —
    # all without blocking the UI from showing immediately. See
    # playnite_sync.py for the honest limitations of this approach.
    playnite_cfg = SETTINGS.setdefault("playnite", {"export_path": None, "executable_path": None})
    playnite_sync.silent_sync_in_background(playnite_cfg, timeout=90)

    start_controller()
    webview.start(debug=False, gui="edgechromium")


if __name__ == "__main__":
    main()
