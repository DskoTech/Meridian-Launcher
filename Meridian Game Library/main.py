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

from crash_logger import install_crash_logging
install_crash_logging("Meridian Game Library")

import system_actions
if system_actions.another_instance_running("Meridian Game Library.exe"):
    sys.exit(0)
from urllib.parse import urlparse, parse_qs

import webview


# pywebview renamed its dialog constants: webview.OPEN_DIALOG and
# webview.FOLDER_DIALOG are deprecated in favor of webview.FileDialog.OPEN
# and .FOLDER. Resolve them once here so we use the new names where they
# exist and still run on older pywebview builds.
try:
    _DLG_OPEN = webview.FileDialog.OPEN
    _DLG_FOLDER = webview.FileDialog.FOLDER
except AttributeError:  # pywebview < 5.x
    _DLG_OPEN = getattr(webview, "OPEN_DIALOG")
    _DLG_FOLDER = getattr(webview, "FOLDER_DIALOG")

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
import theme_assets
import user_themes
import tasks_win
import system_actions
import playnite_import
import playnite_sync
import heroic_import
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
# Backgrounds also accept animated .gif.
BACKGROUND_FILE_TYPES = ("Image Files (*.png;*.jpg;*.jpeg;*.bmp;*.webp;*.gif)",)
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

CACHE_DIR = store.DATA_DIR / ".cache"
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
    result = window.create_file_dialog(_DLG_OPEN, file_types=file_types, allow_multiple=True)
    return list(result) if result else []


# --------------------------------------------------------------------------
# JS-facing API
# --------------------------------------------------------------------------

class Api:
    # ---------------- settings / controls ----------------
    def get_settings(self):
        SETTINGS.setdefault("playnite", {"export_path": None})
        SETTINGS["playnite"]["export_available"] = playnite_import.export_file_available(SETTINGS["playnite"])
        SETTINGS["heroic_available"] = heroic_import.export_file_available()
        SETTINGS.setdefault("game_import_source", "playnite")
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
            _DLG_OPEN,
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

    def get_recently_played_games(self):
        return playnite_import.get_recently_played(self._playnite_settings())

    def _store_login(self, store_key):
        # There's no real per-store "login" anymore — connection state is
        # just "does the Playnite export / Heroic cache exist yet". Kept
        # as a method per store so the frontend's existing login-prompt
        # flow (built for the old per-store auth) still works unchanged.
        if self._import_source() == "heroic":
            if heroic_import.export_file_available():
                return {"success": True}
            return {"success": False, "error": "Heroic Games Launcher isn't installed, or hasn't synced a library yet."}
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
        #
        # This is also the one choke point every game section's entries
        # flow through (storefronts, Heroic, and filter-preset sections
        # alike), so the Start-menu user prefs — hides and renames — are
        # applied here too rather than per-source.
        entries = self._apply_user_game_prefs(entries)
        for entry in entries:
            if entry.get("art"):
                entry["art"] = media_url(entry["art"])
        return entries

    def _apply_user_game_prefs(self, entries):
        hidden = set(SETTINGS.get("hidden_games") or [])
        renames = SETTINGS.get("game_renames") or {}
        show_hidden = bool(SETTINGS.get("show_hidden_games"))
        out = []
        for entry in entries:
            gid = str(entry.get("id"))
            is_hidden = gid in hidden
            if is_hidden and not show_hidden:
                continue
            entry["hidden"] = is_hidden
            if gid in renames and renames[gid]:
                entry["title"] = renames[gid]
            out.append(entry)
        return out

    # ---------------- Start-menu game management ----------------

    def set_game_hidden(self, game_id, hidden):
        gid = str(game_id)
        current = set(SETTINGS.get("hidden_games") or [])
        if hidden:
            current.add(gid)
        else:
            current.discard(gid)
        SETTINGS["hidden_games"] = sorted(current)
        store.save_settings(SETTINGS)
        return SETTINGS

    def set_game_rename(self, game_id, name):
        gid = str(game_id)
        renames = dict(SETTINGS.get("game_renames") or {})
        name = (name or "").strip()
        if name:
            renames[gid] = name
        else:
            renames.pop(gid, None)  # empty name = revert to the real title
        SETTINGS["game_renames"] = renames
        store.save_settings(SETTINGS)
        return SETTINGS

    def set_prefer_xinput(self, enabled):
        """Switch the input backend live. XInput is the proven path;
        GameInput adds Guide-button reporting. Restarts the listener so the
        change takes effect without relaunching the app."""
        SETTINGS["prefer_xinput"] = bool(enabled)
        store.save_settings(SETTINGS)
        restart_controller()
        return SETTINGS

    def controller_debug(self):
        """Deep diagnostics for the Settings controller debugger: which
        backend is live, what GameInput is doing poll-by-poll, and the raw
        state the pad is reporting right now."""
        import gameinput_api
        out = {
            "prefer_xinput": bool(SETTINGS.get("prefer_xinput", False)),
            "env_override": os.environ.get("MERIDIAN_INPUT_BACKEND", "") or None,
            "backend": None,
            "connected": False,
            "backend_errors": dict(getattr(gameinput_api, "LAST_BACKEND_ERRORS", {}) or {}),
            "diag": dict(getattr(gameinput_api, "DIAG", {}) or {}),
            "last_action": _LAST_CONTROLLER_ACTION[0],
            "last_action_age": (
                round(time.time() - _LAST_CONTROLLER_ACTION[1], 1)
                if _LAST_CONTROLLER_ACTION[1] else None
            ),
            "foreground": None,
        }
        listener = _CONTROLLER_LISTENER
        if listener is not None:
            st = listener.status()
            out["backend"] = st.get("backend")
            out["connected"] = st.get("connected")
            out["gamepad_slot"] = getattr(listener.gamepad, "gamepad_state_slot", None)
        try:
            out["foreground"] = self.is_foreground()
        except Exception:
            pass
        return out

    def reset_controller_debug(self):
        import gameinput_api
        gameinput_api.reset_diag()
        return True

    def controller_status(self):
        """Diagnostic for the settings screen: which controller backend is
        active (GameInput / XInput / none) and whether a pad is currently
        connected. Helps confirm whether GameInput is really the path in
        use when debugging fullscreen-experience input problems."""
        env = os.environ.get("MERIDIAN_INPUT_BACKEND", "").strip() or None
        listener = _CONTROLLER_LISTENER
        if listener is None:
            return {"backend": None, "connected": False, "override": env}
        st = listener.status()
        st["override"] = env
        # which IGameInputReading::GetGamepadState vtable slot is in use —
        # confirms GameInput is actually reading the pad, not just loaded.
        try:
            st["gamepad_slot"] = getattr(listener.gamepad, "gamepad_state_slot", None)
        except Exception:
            st["gamepad_slot"] = None
        # why any preferred backend (e.g. GameInput) was rejected, if it was
        try:
            import gameinput_api
            st["backend_errors"] = dict(getattr(gameinput_api, "LAST_BACKEND_ERRORS", {}) or {})
        except Exception:
            st["backend_errors"] = {}
        return st

    def set_show_hidden_games(self, enabled):
        SETTINGS["show_hidden_games"] = bool(enabled)
        store.save_settings(SETTINGS)
        return SETTINGS

    def _import_source(self):
        return SETTINGS.get("game_import_source", "playnite")

    def set_game_import_source(self, source):
        if source not in ("playnite", "heroic"):
            return SETTINGS
        SETTINGS["game_import_source"] = source
        store.save_settings(SETTINGS)
        return SETTINGS

    def _store_get_library(self, store_key):
        if self._import_source() == "heroic":
            entries = heroic_import.get_library(store_key)
        else:
            entries = playnite_import.get_library(store_key, self._playnite_settings())
        return {"entries": self._entries_with_media_urls(entries or [])}

    def _store_sync_library(self, store_key, force=False):
        # "Sync" is just "re-read the export/cache file(s)" for both
        # sources — no network calls, so this is effectively instant. The
        # actual freshness of the data depends on when Playnite/Heroic
        # last wrote their own files.
        if self._import_source() == "heroic":
            entries = heroic_import.get_library(store_key)
        else:
            entries = playnite_import.get_library(store_key, self._playnite_settings())
        if entries is None:
            return {"error": "not_logged_in"}
        return {"entries": self._entries_with_media_urls(entries)}

    def _store_launch(self, game_id, store_key=None):
        if self._import_source() == "heroic":
            runner = {"epic": "legendary", "gog": "gog", "other": "sideload"}.get(store_key, "legendary")
            heroic_import.launch_game(game_id, runner=runner)
        else:
            playnite_import.launch_game(game_id, self._playnite_settings())

    def _store_install_or_uninstall(self, game_id):
        if self._import_source() == "heroic":
            heroic_import.show_in_launcher(game_id)
        else:
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

    def other_source_get_library(self, source_id):
        """Games under one specific non-big-5 platform (PC, PlayStation,
        Nintendo Switch, etc, for anything whose SOURCE isn't Steam/GOG/
        Epic/Amazon) — each platform becomes its own section instead of
        everything sharing one "Other" bucket. Playnite-only; Heroic's
        library is already just epic/gog/other with no further per-
        platform breakdown to make."""
        if self._import_source() == "heroic":
            return {"entries": []}
        entries = playnite_import.get_other_source_library(source_id, self._playnite_settings())
        return {"entries": self._entries_with_media_urls(entries or [])}

    def list_other_game_sources(self):
        """[{"id", "name", "count"}] for Settings and for buildCategories to
        turn into one section per distinct non-big-5 platform."""
        if self._import_source() == "heroic":
            return []
        return playnite_import.get_other_sources(self._playnite_settings())

    def set_other_source_sections(self, enabled):
        SETTINGS["other_source_sections"] = bool(enabled)
        store.save_settings(SETTINGS)
        return SETTINGS

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
        self._store_launch(game_id, "steam")

    def gog_launch(self, game_id):
        self._store_launch(game_id, "gog")

    def epic_launch(self, game_id):
        self._store_launch(game_id, "epic")

    def amazon_launch(self, game_id):
        self._store_launch(game_id, "amazon")

    def other_launch(self, game_id):
        self._store_launch(game_id, "other")

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
        result = webview.windows[0].create_file_dialog(_DLG_FOLDER)
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
    # ---------------- open-programs bar (taskbar replacement) ----------------
    def list_open_tasks(self):
        return tasks_win.list_open_tasks()

    def focus_task(self, hwnd):
        return {"ok": tasks_win.focus_task(hwnd)}

    def close_task(self, hwnd):
        return {"ok": tasks_win.close_task(hwnd)}

    def set_foreground_trigger(self, mode):
        if mode not in ("start_select", "xbox", "off"):
            return SETTINGS
        SETTINGS["foreground_trigger"] = mode
        store.save_settings(SETTINGS)
        return SETTINGS

    def is_foreground(self):
        """Whether this app's window is the OS foreground window right now.
        The frontend uses this to gate controller navigation: input is still
        received in the background (so the foreground combo works), but it
        shouldn't move the cursor or open menus until the app is focused."""
        try:
            import ctypes
            hwnd = ctypes.windll.user32.GetForegroundWindow()
            our = ctypes.windll.user32.FindWindowW(None, APP_TITLE)
            return bool(hwnd and our and hwnd == our)
        except Exception:
            return True  # non-Windows or failure: don't gate

    def set_close_tasks_without_prompt(self, enabled):
        SETTINGS["close_tasks_without_prompt"] = bool(enabled)
        store.save_settings(SETTINGS)
        return SETTINGS

    def _layout_key(self):
        return SETTINGS.get("layout", "dawning_horizon")

    def theme_asset_urls(self):
        assets = str(store.ASSETS_DIR)
        layout = self._layout_key()
        bg = theme_assets.placeholder_background(assets, "library", layout)
        ov = theme_assets.placeholder_overlay(assets, "library", layout)
        return {
            "background": media_url(bg) if bg else None,
            "overlay": media_url(ov) if ov else None,
        }

    def set_background(self):
        # pywebview file_types are filter STRINGS; concatenating a list of
        # tuples raises TypeError and the dialog never opens.
        paths = _open_file_dialog(BACKGROUND_FILE_TYPES)
        if paths:
            SETTINGS.setdefault("background_by_theme", {})[self._layout_key()] = paths[0]
            store.save_settings(SETTINGS)
        return SETTINGS

    def clear_background(self):
        SETTINGS.setdefault("background_by_theme", {}).pop(self._layout_key(), None)
        store.save_settings(SETTINGS)
        return SETTINGS

    def set_overlay(self):
        paths = _open_file_dialog(IMAGE_FILE_TYPES)
        if paths:
            try:
                from PIL import Image
                layout = self._layout_key()
                dest = store.DATA_DIR / f"overlay_{layout}.png"
                Image.open(paths[0]).convert("RGBA").save(dest, "PNG")
                SETTINGS.setdefault("overlay_by_theme", {})[layout] = str(dest)
                SETTINGS.setdefault("overlay_enabled_by_theme", {})[layout] = True
            except Exception:
                pass
            store.save_settings(SETTINGS)
        return SETTINGS

    def set_overlay_enabled(self, enabled):
        SETTINGS.setdefault("overlay_enabled_by_theme", {})[self._layout_key()] = bool(enabled)
        store.save_settings(SETTINGS)
        return SETTINGS

    def clear_overlay(self):
        layout = self._layout_key()
        SETTINGS.setdefault("overlay_by_theme", {}).pop(layout, None)
        SETTINGS.setdefault("overlay_enabled_by_theme", {})[layout] = False
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

    def set_games_per_row(self, n):
        if n not in (3, 4, 5):
            return SETTINGS
        SETTINGS["games_per_row"] = n
        store.save_settings(SETTINGS)
        return SETTINGS

    def set_display_type(self, store_id, display_type):
        if display_type not in ("list", "gallery"):
            return SETTINGS
        SETTINGS.setdefault("display_type", {})[store_id] = display_type
        store.save_settings(SETTINGS)
        return SETTINGS

    def set_window_mode(self, mode):
        """Window mode, matching Meridian Launcher's four modes:
        exclusive_fullscreen (true OS fullscreen), windowed_fullscreen
        (borderless, covering the screen), windowed, and kiosk. The frame
        itself can't be added/removed at runtime (pywebview limitation), so
        a live switch between framed/frameless fully applies on restart."""
        SETTINGS["window_mode"] = mode
        store.save_settings(SETTINGS)
        try:
            win = webview.windows[0]
            is_exclusive = getattr(win, "_meridian_exclusive_fs", False)
            if mode == "exclusive_fullscreen":
                if not is_exclusive:
                    win.toggle_fullscreen()
                    win._meridian_exclusive_fs = True
                win._meridian_fullscreen = True
            elif mode in ("windowed_fullscreen", "kiosk"):
                if is_exclusive:
                    win.toggle_fullscreen()
                    win._meridian_exclusive_fs = False
                if not getattr(win, "_meridian_fullscreen", False):
                    win.move(0, 0)
                    win._meridian_fullscreen = True
            elif mode == "windowed":
                if is_exclusive:
                    win.toggle_fullscreen()
                    win._meridian_exclusive_fs = False
                if getattr(win, "_meridian_fullscreen", False):
                    win.move(60, 60)
                    win._meridian_fullscreen = False
        except Exception:
            pass
        return SETTINGS

    def set_layout(self, mode):
        """UI layout mode: 'night_horizon' (default) or 'cyber_radial'. Purely
        a frontend concern — the frontend toggles a body class off this and
        does all the actual layout work; the backend just persists it."""
        # Built-in layouts, or any discovered user theme ("user-<slug>").
        valid = mode in ("dawning_horizon", "night_horizon", "cyber_radial")
        if not valid and mode.startswith("user-"):
            valid = user_themes.get_theme(BASE_DIR, mode) is not None
        if not valid:
            return SETTINGS
        SETTINGS["layout"] = mode
        store.save_settings(SETTINGS)
        return SETTINGS

    def list_user_themes(self):
        """User themes discovered in the themes/ folder next to the app.
        The frontend adds these to the theme picker and injects each theme's
        CSS on top of its chosen base layout. Safe to call anytime; returns
        [] when the folder is empty or missing."""
        try:
            return user_themes.discover_themes(BASE_DIR)
        except Exception:
            return []

    def get_user_theme_css(self, layout_value):
        """The CSS + base layout for one user theme, by its 'user-<slug>'
        settings value. Returns None if it's not a user theme or is gone."""
        try:
            t = user_themes.get_theme(BASE_DIR, layout_value)
            if not t:
                return None
            return {"css": t["css"], "base": t["base"], "name": t["name"]}
        except Exception:
            return None

    def set_dawning_theme_color(self, value):
        """Dawning Horizon primary theme color: "original", or
        "<palette>:<hue>". Like set_layout, the backend only validates and
        persists — the frontend computes the actual HSL values."""
        if value != "original":
            parts = str(value).split(":")
            if len(parts) != 2:
                return SETTINGS
            palette, hue = parts
            if palette not in ("light", "dark", "neon", "primary", "pastel", "bubblegum", "hex"):
                return SETTINGS
            if palette == "hex":
                # Custom color from the grid selector: "hex:#rrggbb".
                h = hue.lstrip("#")
                if len(h) != 6 or any(ch not in "0123456789abcdefABCDEF" for ch in h):
                    return SETTINGS
            elif hue not in ("red", "orange", "yellow", "green", "blue", "indigo", "violet"):
                return SETTINGS
        SETTINGS["dawning_theme_color"] = value
        store.save_settings(SETTINGS)
        return SETTINGS

    # ---------------- settings: app data folder ----------------
    def open_app_data_folder(self):
        """Opens %LOCALAPPDATA%\\Meridian Launcher\\Meridian Game Library\\
        in Explorer, then makes sure onscreenmenu is running (launched if it
        wasn't already) so a controller can be used to navigate the folder."""
        ok, err = system_actions.open_folder(str(store.DATA_DIR))
        if ok:
            _maybe_launch_onscreenmenu()
        return {"ok": ok, "error": err}


# --------------------------------------------------------------------------
# Controller wiring
# --------------------------------------------------------------------------

def _maybe_launch_onscreenmenu():
    """Best-effort launch of the on-screen menu companion via osm.bat (not
    onscreenmenu.exe directly) from the app's own folder, but only if
    onscreenmenu.exe isn't already running — used after opening the app
    data folder so the on-screen menu companion is available to navigate
    it with a controller."""
    if system_actions.is_process_running("onscreenmenu.exe"):
        return
    bat = BASE_DIR / "osm.bat"
    if bat.exists():
        try:
            system_actions.launch_path(str(bat))
        except Exception:
            pass


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



# [action_name, timestamp] of the most recent controller action to reach the
# app — the settings debugger uses it to prove input is (or isn't) arriving.
_LAST_CONTROLLER_ACTION = [None, 0.0]


def restart_controller():
    """Stop the running listener and start a fresh one, so a backend change
    (prefer_xinput) applies without relaunching the app."""
    global _CONTROLLER_LISTENER
    try:
        if _CONTROLLER_LISTENER is not None:
            _CONTROLLER_LISTENER.stop()
    except Exception:
        pass
    _CONTROLLER_LISTENER = None
    try:
        import gameinput_api
        gameinput_api.reset_diag()
    except Exception:
        pass
    return start_controller()


def _controller_action(action_name):
    # record it for the settings debugger before dispatching
    _LAST_CONTROLLER_ACTION[0] = action_name
    _LAST_CONTROLLER_ACTION[1] = time.time()
    try:
        webview.windows[0].evaluate_js(f"window.handleControllerInput && window.handleControllerInput('{action_name}')")
    except Exception:
        pass


def _controller_any():
    try:
        webview.windows[0].evaluate_js("window.handleControllerAny && window.handleControllerAny()")
    except Exception:
        pass


_CONTROLLER_LISTENER = None  # kept for the settings screen's controller_status()


def start_controller():
    global _CONTROLLER_LISTENER
    controls = store.load_controller_controls()
    listener = ControllerListener(
        controls,
        on_action=_controller_action,
        on_any=_controller_any,
        on_quit_combo=_quit_via_combo,
        on_foreground_combo=_bring_to_foreground,
        foreground_trigger_getter=lambda: SETTINGS.get("foreground_trigger", "start_select"),
        prefer_xinput=bool(SETTINGS.get("prefer_xinput", False)),
    )
    _CONTROLLER_LISTENER = listener
    listener.start()
    return listener


# --------------------------------------------------------------------------
# Boot: resolution detection, window creation
# --------------------------------------------------------------------------



def detect_screen_size():
    try:
        user32 = ctypes.windll.user32
        return user32.GetSystemMetrics(0), user32.GetSystemMetrics(1)
    except Exception:
        return 1280, 800


def main():
   

    width, height = detect_screen_size()
    mode = SETTINGS.get("window_mode", "fullscreen")
    # Meridian Launcher passes --window-mode=borderless-fullscreen when it
    # opens this app (via the Games section's Game Library entry), asking
    # for windowed (borderless) fullscreen for this run regardless of
    # whatever was last saved. This is only applied to this run, not
    # persisted, so a person's own saved window mode (set from this app's
    # own settings) survives the next time they open it by hand.
    if "--window-mode=borderless-fullscreen" in sys.argv:
        mode = "fullscreen"
    # Borderless (windowed) fullscreen instead of OS-exclusive fullscreen:
    # a frameless window sized and positioned to exactly cover the screen.
    borderless_fullscreen = mode == "fullscreen"
    frameless = borderless_fullscreen

    api = Api()
    window = webview.create_window(
        APP_TITLE,
        str(BASE_DIR / "frontend" / "index.html"),
        js_api=api,
        x=0 if borderless_fullscreen else None,
        y=0 if borderless_fullscreen else None,
        width=width,
        height=height,
        min_size=(1024, 640),
        background_color="#05070d",
        fullscreen=False,
        frameless=frameless,
    )
    window._meridian_fullscreen = borderless_fullscreen

    # NOTE: Playnite is deliberately NOT launched on startup anymore. The
    # gallery reads whatever the last export produced; refreshing the
    # library is now an explicit user action ("Sync Playnite now" in
    # Settings), so opening the gallery never spawns Playnite.
    SETTINGS.setdefault("playnite", {"export_path": None, "executable_path": None})

    start_controller()
    webview.start(debug=False, gui="edgechromium")


if __name__ == "__main__":
    main()
