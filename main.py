"""
MeridianLauncher — a Windows media hub / app launcher front-end.

Sections: Music, Photos, Videos, Apps, Games, Emulators, Chat, Streaming,
Web, Files, System, Macros, plus user-defined custom sections. Navigable by
keyboard, mouse, or game controller (XInput).
"""

import ctypes
import hashlib
import json
import mimetypes
import os
import time
import shutil
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from crash_logger import install_crash_logging
install_crash_logging("Meridian Launcher")

import system_actions
if system_actions.another_instance_running("MeridianLauncher.exe"):
    sys.exit(0)
import fullscreen_helper
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

import store
import system_actions
import tasks_win
import explorer_shell
import user_themes
import theme_assets
import updater
import plugin_manager
from controller_input import ControllerListener

# Recently-played games are sourced from Game Library's own Playnite
# integration (real, comprehensive play history) rather than Launcher
# tracking its own separate, much-smaller local history. Game Library
# ships as a sibling folder of this install; playnite_import.py has no
# webview/GUI dependencies, so it's safe to import directly rather than
# reimplementing the same Playnite-export parsing and launch logic here.
_GAME_LIBRARY_DIR = Path(__file__).resolve().parent / "Meridian Game Library"
if str(_GAME_LIBRARY_DIR) not in sys.path:
    sys.path.insert(0, str(_GAME_LIBRARY_DIR))
try:
    import playnite_import
except ImportError:
    playnite_import = None  # Game Library isn't installed alongside this copy of Launcher

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

# 1. Check if the app is bundled/compiled into an EXE (PyInstaller)
if getattr(sys, 'frozen', False):
    # Get the directory where the main compiled .exe actually sits
    BASE_DIR = Path(sys.executable).parent
else:
    # Running as standard script; get directory of the current Python file
    BASE_DIR = Path(__file__).resolve().parent


def _resource_path(*parts):
    """Path to a bundled read-only resource, from source or from a frozen
    (onefile) PyInstaller build. Onefile builds extract bundled `datas`
    into a temporary _MEIPASS folder at startup rather than leaving them
    next to the exe (BASE_DIR), so this has to check for that separately.
    """
    base = Path(getattr(sys, "_MEIPASS", BASE_DIR))
    return base.joinpath(*parts)


CURRENT_VERSION = updater.get_local_version(str(_resource_path("VERSION")))

APP_TITLE = "MeridianLauncher"

# Passed to the other Meridian apps (CyberDeckBrowser.exe, "Meridian Game
# Library.exe", onscreenmenu.exe) when Meridian Launcher opens them, asking
# them to open in windowed (borderless) fullscreen rather than whatever
# window mode they last had saved. Those apps understand this flag;
# arbitrary third-party apps (Apps/Games/Emulators sections) don't, so they
# still only get the best-effort "start maximized" hint in
# system_actions.launch_path.
WINDOW_MODE_REQUEST_FLAG = "--window-mode=borderless-fullscreen"

MUSIC_EXT = {".mp3", ".flac", ".wav", ".m4a", ".ogg", ".wma", ".aac"}
PHOTO_EXT = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"}
VIDEO_EXT = {".mp4", ".mkv", ".avi", ".mov", ".wmv", ".webm", ".m4v"}
IMAGE_FILE_TYPES = ("Image Files (*.png;*.jpg;*.jpeg;*.bmp;*.webp)",)
# Backgrounds also accept animated .gif (shown on a CSS layer that animates).
BACKGROUND_FILE_TYPES = ("Image Files (*.png;*.jpg;*.jpeg;*.bmp;*.webp;*.gif)",)
VIDEO_FILE_TYPES = ("Video Files (*.mp4;*.webm;*.mov;*.mkv;*.avi)",)
EXE_FILE_TYPES = ("Executable Files (*.exe)",)
BAT_FILE_TYPES = ("Batch Files (*.bat)",)
SCRIPT_FILE_TYPES = ("Scripts (*.bat;*.ps1)",)

SETTINGS = store.load_settings()
store.ensure_controls_files()

_explorer_box_proc = None  # Popen handle for the boxed (non-fullscreen) Meridian FileBrowse instance, if any
_browser_box_proc = None  # Popen handle for the boxed (non-fullscreen) Meridian NetBrowse instance, if any
_plugin_webapp_procs = {}  # plugin_id -> Popen handle, for "webapp"-type plugins (Telegram/Discord/etc)


def _rescan_plugins():
    """Discover Plugins/ folders and merge them into SETTINGS["plugins"],
    preserving each existing plugin's visibility flag and adding new ones
    hidden by default. Called once at startup and again from the Settings
    > Plugins "Rescan" button."""
    discovered = plugin_manager.scan_plugins()
    existing = SETTINGS.get("plugins", {})
    merged = {}
    for info in discovered:
        pid = info["id"]
        entry = {
            "label": info["label"],
            "type": info.get("type", "list"),
            "visible": bool(existing.get(pid, {}).get("visible", False)),
        }
        if info.get("type") in ("webapp", "option"):
            entry["url"] = info.get("url", "")
        if info.get("type") == "option":
            entry["section"] = info.get("section", "chat")
        merged[pid] = entry
    SETTINGS["plugins"] = merged
    store.save_settings(SETTINGS)
    return discovered


_rescan_plugins()


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

    def _handle_open_explorer(self, parsed):
        """Local-only endpoint used by the 'Make Meridian FileBrowse the
        default shell browser' trampoline: brings Meridian Launcher to the
        foreground, switches it to the Explorer section, and loads the
        requested folder into Meridian FileBrowse there."""
        qs = parse_qs(parsed.query)
        path = qs.get("path", [""])[0]
        try:
            _bring_to_foreground()
            escaped = path.replace("\\", "\\\\").replace("'", "\\'")
            webview.windows[0].evaluate_js(
                f"window.__meridianOpenPathInExplorer && window.__meridianOpenPathInExplorer('{escaped}')"
            )
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"ok")
        except Exception:
            try:
                self.send_error(500)
            except Exception:
                pass

    def _handle_open_browser(self, parsed):
        """Local-only endpoint used by the 'Make Meridian NetBrowse the
        default system web browser' trampoline: brings Meridian Launcher
        to the foreground, switches it to the Browser section, and loads
        the requested URL into Meridian NetBrowse there."""
        qs = parse_qs(parsed.query)
        url = qs.get("url", [""])[0]
        try:
            _bring_to_foreground()
            escaped = url.replace("\\", "\\\\").replace("'", "\\'")
            webview.windows[0].evaluate_js(
                f"window.__meridianOpenUrlInBrowser && window.__meridianOpenUrlInBrowser('{escaped}')"
            )
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"ok")
        except Exception:
            try:
                self.send_error(500)
            except Exception:
                pass

    def _handle_plugin_exited(self, parsed):
        """Fast path for handing focus/controls back to Meridian Launcher
        the INSTANT a boxed CyberDeckBrowser window closes, rather than
        waiting for proc.wait() to notice the whole process has actually
        exited. QtWebEngine/Chromium teardown after closeEvent can take a
        while even after the window itself has visually gone - CyberDeck-
        Browser calls this (best-effort, from its own closeEvent) right
        before it starts that teardown, so this doesn't wait on it at all.
        The proc.wait()-based watcher threads still run as a backup/
        cleanup path in case this call never arrives (e.g. a crash)."""
        qs = parse_qs(parsed.query)
        which = qs.get("which", [""])[0]
        try:
            suspend_main_controls(False)
            escaped = which.replace("'", "\\'")
            webview.windows[0].evaluate_js(
                f"window.onEmbeddedPluginExited && window.onEmbeddedPluginExited('{escaped}')"
            )
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"ok")
        except Exception:
            try:
                self.send_error(500)
            except Exception:
                pass

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/internal/open-explorer":
            self._handle_open_explorer(parsed)
            return
        if parsed.path == "/internal/open-browser":
            self._handle_open_browser(parsed)
            return
        if parsed.path == "/internal/plugin-exited":
            self._handle_plugin_exited(parsed)
            return
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
    try:
        (store.DATA_DIR / "internal_port.txt").write_text(str(port), encoding="utf-8")
    except Exception:
        pass
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
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
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
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
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
            SETTINGS["sections"].setdefault(section_id, {"items": [], "launch_with_osm": True})
            return SETTINGS["sections"][section_id]
    return None


def _section_launches_with_osm(section_id):
    """Whether launching something from this section should also bring up
    onscreenmenu. Sections with their own stored settings (apps/games/
    emulators/chat/streaming/custom) use their own "launch_with_osm" flag.
    Desktop has no such entry (it's scanned live from the real Windows
    Desktop, not a user-managed list), so it previously silently never
    triggered osm.bat at all - defaulting to True here (same default every
    other section already uses) instead of treating a missing entry as
    "don't launch" fixes that."""
    sec = _section_store(section_id)
    if sec is not None:
        return sec.get("launch_with_osm", True)
    return True


def _scan_desktop_folder():
    """Whatever's sitting on the user's actual Windows Desktop right now —
    shortcuts, exes, files, folders — re-scanned fresh every time the
    Desktop section is opened rather than cached, since this reflects
    live desktop contents, not a curated Meridian list. Hidden/system
    files (desktop.ini etc.) are skipped. Folders are included (tagged
    "is_dir": True) so they can be routed to the Explorer section /
    Meridian Explorer / Windows Explorer instead of launch_path (which
    requires os.path.isfile())."""
    desktop = Path(os.environ.get("USERPROFILE", str(Path.home()))) / "Desktop"
    if not desktop.exists():
        return []
    items = []
    try:
        for entry in sorted(desktop.iterdir(), key=lambda p: p.name.lower()):
            if entry.name.startswith(".") or entry.name.lower() == "desktop.ini":
                continue
            try:
                if entry.is_dir():
                    items.append({"path": str(entry), "name": entry.name, "is_dir": True})
                elif entry.is_file():
                    items.append({"path": str(entry), "name": store.display_name(str(entry)), "is_dir": False})
            except OSError:
                continue
    except OSError:
        return []
    return items


def _game_library_playnite_settings():
    """Game Library's real user data lives under %LOCALAPPDATA%\\Meridian
    Launcher\\Meridian Game Library\\settings.json (not next to its exe —
    see that app's store.py for the same convention Launcher itself uses).
    Returns a settings dict shaped the way playnite_import.py expects,
    even when the file can't be read, so callers don't need their own
    fallback logic."""
    local_appdata = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
    settings_path = Path(local_appdata) / "Meridian Launcher" / "Meridian Game Library" / "settings.json"
    try:
        with open(settings_path, encoding="utf-8") as f:
            data = json.load(f)
        return data.get("playnite") or {"export_path": None, "executable_path": None}
    except (OSError, json.JSONDecodeError):
        return {"export_path": None, "executable_path": None}


def _record_recent_game(path):
    """Track the last few games launched from the Games section, most-recent-
    first, capped at 5 — shown right after the Game Library tile in the
    Games gallery. Local to Meridian Launcher's own exe-list section, not
    pulled from the separate Meridian Game Library app's Playnite history."""
    sec = _section_store("games")
    existing = next((it for it in sec["items"] if it["path"] == path), None) if sec else None
    name = existing["name"] if existing else store.display_name(path)
    recents = SETTINGS.setdefault("recent_games", [])
    recents[:] = [r for r in recents if r["path"] != path]
    recents.insert(0, {"path": path, "name": name})
    del recents[5:]
    store.save_settings(SETTINGS)


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


def _maybe_launch_osm():
    """Best-effort launch of osm.bat (the on-screen-menu companion script)
    from the app's own folder. Silently does nothing if the file isn't
    there — the toggle that triggers this defaults to on, so a missing
    osm.bat shouldn't spam the user with error toasts."""
    bat = BASE_DIR / "osm.bat"
    if bat.exists():
        try:
            system_actions.launch_path(str(bat))
        except Exception:
            pass


def _maybe_launch_onscreenmenu():
    """Best-effort launch of the on-screen menu companion via osm.bat (not
    onscreenmenu.exe directly) from the app's own folder, but only if
    onscreenmenu.exe isn't already running — used after opening the app
    data folder so the on-screen menu companion is available to navigate
    it with a controller."""
    if system_actions.is_process_running("onscreenmenu.exe"):
        return
    _maybe_launch_osm()


def _apply_kiosk_disable():
    """Shared by every kiosk-exit path (secret code, 45s Y hold, factory
    reset): flips window_mode back to fullscreen, persists it. The app uses
    borderless windowed fullscreen (a frameless window sized/positioned to
    exactly cover the screen) instead of OS-exclusive fullscreen, so kiosk
    and plain fullscreen are already the same size/position — there's
    nothing to resize here. Note: pywebview can't drop a window's frameless
    flag at runtime, so a window created frameless (kiosk) will still need
    an app restart to regain its title bar if the person later switches to
    windowed mode."""
    SETTINGS["window_mode"] = "windowed_fullscreen"
    store.save_settings(SETTINGS)
    try:
        win = webview.windows[0]
        win._meridian_fullscreen = True
    except Exception:
        pass


# --------------------------------------------------------------------------
# Background thumbnail/metadata precaching
# --------------------------------------------------------------------------
# scan_library/browse_folder already only regenerate a thumbnail when a
# file's mtime doesn't match what's cached, so calling this machinery
# proactively — before the person has actually opened the section — is
# cheap once warm and just moves the one-time cost earlier instead of
# making the first visit feel slow.

def _scan_library_impl(kind):
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


def _browse_folder_impl(kind, path, precache_subfolders=True):
    """Non-recursive single-directory listing, used by the subfolder
    navigation sidebar when Load Subfolders is disabled. Also kicks off a
    background thread to warm the thumbnail cache for every subfolder
    underneath this one, so descending further is already fast by the
    time the person gets there."""
    extmap = {"music": MUSIC_EXT, "photos": PHOTO_EXT, "videos": VIDEO_EXT}
    if kind not in extmap or not path or not os.path.isdir(path):
        return {"path": path, "subfolders": [], "items": []}
    subfolders = _list_subfolders(path)
    entries = {p: _build_entry(kind, p) for p in _scan_flat(path, extmap[kind])}
    if precache_subfolders and subfolders:
        threading.Thread(target=_precache_folder_recursive, args=(kind, path), daemon=True).start()
    return {"path": path, "subfolders": subfolders, "items": _entries_to_response(kind, entries)}


def _precache_folder_recursive(kind, root_path):
    """Walk root_path and every subfolder underneath it, warming the
    thumbnail/metadata cache for each matching file. Safe to call
    liberally — every thumb/metadata function it bottoms out in already
    checks for an existing cached file first, so re-visiting an
    already-warm path costs almost nothing."""
    extmap = {"music": MUSIC_EXT, "photos": PHOTO_EXT, "videos": VIDEO_EXT}
    ext = extmap.get(kind)
    if not ext:
        return
    try:
        for dirpath, _dirnames, filenames in os.walk(root_path):
            for fname in filenames:
                if os.path.splitext(fname)[1].lower() in ext:
                    try:
                        _build_entry(kind, os.path.join(dirpath, fname))
                    except Exception:
                        continue
    except Exception:
        pass


def _precache_all_libraries():
    """Warm the whole configured library (music/videos/photos) in the
    background at startup, so the first visit to each section is already
    fast instead of generating thumbnails on demand right as the person
    opens it."""
    for kind in ("videos", "music", "photos"):  # videos first — the slowest per-file (ffmpeg)
        try:
            _scan_library_impl(kind)
        except Exception:
            continue
        for folder in SETTINGS["folders"].get(kind, []):
            if os.path.isdir(folder):
                _precache_folder_recursive(kind, folder)


def start_background_precache():
    threading.Thread(target=_precache_all_libraries, daemon=True).start()


# --------------------------------------------------------------------------
# JS-facing API
# --------------------------------------------------------------------------

class Api:
    # ---------------- settings / controls ----------------
    def get_settings(self):
        return SETTINGS

    def get_keyboard_controls(self):
        return store.load_keyboard_controls()

    def get_controller_controls(self):
        return store.load_controller_controls()

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
        return _scan_library_impl(kind)

    def browse_folder(self, kind, path):
        return _browse_folder_impl(kind, path)

    def delete_thumbnail_cache(self):
        """Settings > Delete Thumbnail Cache. Clears every generated thumb
        plus the mtime index caches, so the next scan rebuilds everything
        from scratch (background precache picks it back up right away)."""
        cleared = 0
        try:
            for f in CACHE_DIR.iterdir():
                try:
                    f.unlink()
                    cleared += 1
                except OSError:
                    continue
            for kind in ("music", "videos", "photos"):
                p = _index_cache_path(kind)
                if p.exists():
                    p.unlink()
        except Exception as e:
            return {"ok": False, "error": str(e)}
        start_background_precache()
        return {"ok": True, "cleared": cleared}

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

    def launch_exe(self, path, section_id=None):
        # Folder shortcuts are first-class launchable items: a directory
        # path opens in Meridian Explorer (when the routing setting is on
        # and it's installed alongside) or Windows Explorer otherwise.
        if path and os.path.isdir(path):
            ok, err = _open_folder_routed(path)
            if ok and section_id and _section_launches_with_osm(section_id):
                _maybe_launch_osm()
            return {"ok": ok, "error": err}
        if (SETTINGS.get("fullscreen_helper_enabled")
                and path and os.path.splitext(path)[1].lower() == ".exe"):
            ok, err = fullscreen_helper.launch_and_enforce_fullscreen(path)
            if not ok:
                # Fall back to the normal launch path rather than failing
                # the launch outright if the helper couldn't run.
                ok, err = system_actions.launch_path(path)
        else:
            ok, err = system_actions.launch_path(path)
        if ok and section_id:
            if _section_launches_with_osm(section_id):
                _maybe_launch_osm()
            if section_id == "games":
                _record_recent_game(path)
        return {"ok": ok, "error": err}

    def get_recent_games(self):
        if playnite_import is not None:
            recents = playnite_import.get_recently_played(_game_library_playnite_settings())
            if recents:
                return [
                    {"__playnite": True, "id": e["id"], "name": e["title"], "iconUrl": media_url(e["art"]) if e["art"] else None}
                    for e in recents
                ]
        # Game Library isn't installed alongside this copy, or Playnite
        # isn't connected there yet, or nothing's been played through it —
        # fall back to Launcher's own (much smaller) local launch history.
        return _with_icons(SETTINGS.get("recent_games", []))

    def launch_recent_game(self, game_id):
        if playnite_import is None:
            return {"ok": False, "error": "Meridian Game Library isn't installed alongside this copy of Launcher."}
        try:
            playnite_import.launch_game(game_id, _game_library_playnite_settings())
            return {"ok": True, "error": None}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    # ---------------- Desktop section (auto-populated, off by default) ----------------
    def list_desktop_items(self):
        return _with_icons(_scan_desktop_folder())

    def set_builtin_section_visible(self, section_id, visible):
        hidden = set(SETTINGS.get("hidden_builtin_sections", []))
        if visible:
            hidden.discard(section_id)
        else:
            hidden.add(section_id)
        SETTINGS["hidden_builtin_sections"] = sorted(hidden)
        store.save_settings(SETTINGS)
        return SETTINGS

    def set_desktop_section_enabled(self, enabled):
        SETTINGS["desktop_section_enabled"] = bool(enabled)
        store.save_settings(SETTINGS)
        return SETTINGS

    def set_explorer_section_enabled(self, enabled):
        SETTINGS["explorer_section_enabled"] = bool(enabled)
        store.save_settings(SETTINGS)
        return SETTINGS

    def set_browser_section_enabled(self, enabled):
        SETTINGS["browser_section_enabled"] = bool(enabled)
        store.save_settings(SETTINGS)
        return SETTINGS

    def set_display_type(self, section_id, display_type):
        """Per-section 'List Style' vs 'Gallery Style' — same generic toggle
        for any section (media or exe-list). Purely a frontend rendering
        concern; the backend just persists which one each section is on."""
        if display_type not in ("list", "gallery"):
            return SETTINGS
        SETTINGS.setdefault("display_type", {})[section_id] = display_type
        store.save_settings(SETTINGS)
        return SETTINGS

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
        SETTINGS["sections"][sid] = {"items": [], "launch_with_osm": True}
        store.save_settings(SETTINGS)
        return SETTINGS

    def remove_custom_section(self, section_id):
        SETTINGS["custom_sections"] = [cs for cs in SETTINGS["custom_sections"] if cs["id"] != section_id]
        SETTINGS["sections"].pop(section_id, None)
        store.save_settings(SETTINGS)
        return SETTINGS

    # ---------------- Plugins (auto-discovered custom sections) ----------------
    def load_plugin_webapp_box(self, plugin_id, x, y, w, h):
        """Boxes a CyberDeckBrowser instance pinned to a plugin's fixed
        URL (Telegram/Discord/Messenger/Snapchat/etc — see Plugins/*/plugin.json
        "url") into that plugin section's list-frame box. Same mechanism as
        the Browser section's load_browser_box, but launched with
        --minimal-menu (Y/X menus stripped to just "Exit Program") and
        tracked per plugin_id so multiple webapp plugins never clobber each
        other's process. (Meridian NetBrowse used to be a separate app for
        this — merged back into CyberDeckBrowser itself via --box=/
        --minimal-menu, since running two full QtWebEngine/Chromium
        bundles side by side was the single biggest contributor to the
        suite's compiled size.)"""
        global _plugin_webapp_procs
        url = plugin_manager.get_plugin_url(plugin_id)
        if not url:
            return {"ok": False, "error": "This plugin has no url configured in its plugin.json."}
        exe = BASE_DIR / "CyberDeckBrowser.exe"
        if not exe.exists():
            return {"ok": False, "error": "CyberDeckBrowser.exe not found in the app folder."}
        self.unload_plugin_webapp_box(plugin_id)
        try:
            args = [str(exe), f"--box={int(x)},{int(y)},{int(w)},{int(h)}", "--minimal-menu",
                    f"--notify-exit={plugin_id}", url]
            proc = subprocess.Popen(
                args, cwd=str(BASE_DIR),
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            _plugin_webapp_procs[plugin_id] = proc
            suspend_main_controls(True)
            threading.Thread(target=_watch_plugin_webapp_exit, args=(plugin_id, proc), daemon=True).start()
            return {"ok": True, "error": None}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def unload_plugin_webapp_box(self, plugin_id):
        """Terminate the boxed process for this plugin, if any, so it
        doesn't keep running in the background once the user leaves that
        section, and hand Meridian Launcher's own controls back."""
        global _plugin_webapp_procs
        proc = _plugin_webapp_procs.pop(plugin_id, None)
        if proc is not None:
            try:
                if proc.poll() is None:
                    proc.terminate()
            except Exception:
                pass
        suspend_main_controls(False)
        return {"ok": True, "error": None}

    def rescan_plugins(self):
        """Re-scan Plugins/ on demand (Settings > Plugins > Rescan)."""
        for pid in list(SETTINGS.get("plugins", {}).keys()):
            plugin_manager.unload_backend(pid)
        _rescan_plugins()
        return SETTINGS

    def list_plugins(self):
        """Ordered list of discovered plugins with their visibility. "list"/
        "webapp" plugins appear after the last custom section; "option"
        plugins don't get their own section at all — see
        list_section_options() for how those surface instead."""
        discovered = plugin_manager.scan_plugins()
        out = []
        for info in discovered:
            pid = info["id"]
            entry = SETTINGS.get("plugins", {}).get(pid, {"visible": False})
            item = {
                "id": pid, "label": info["label"], "type": info.get("type", "list"),
                "visible": bool(entry.get("visible", False)),
            }
            if info.get("type") == "option":
                item["section"] = info.get("section", "chat")
            out.append(item)
        return out

    def list_section_options(self, section_id):
        """[{"id","label","pluginId"}] — the enabled "option"-type plugins
        targeting this section id (e.g. "chat"), in discovery order. Used
        to build a section (like Chat) whose entries are individually
        toggleable plugins rather than a fixed list."""
        discovered = plugin_manager.scan_plugins()
        out = []
        for info in discovered:
            if info.get("type") != "option" or info.get("section", "chat") != section_id:
                continue
            pid = info["id"]
            entry = SETTINGS.get("plugins", {}).get(pid, {"visible": False})
            if not entry.get("visible", False):
                continue
            out.append({"id": pid, "label": info["label"]})
        return out

    def set_plugin_visible(self, plugin_id, visible):
        SETTINGS.setdefault("plugins", {}).setdefault(plugin_id, {"visible": False})
        SETTINGS["plugins"][plugin_id]["visible"] = bool(visible)
        store.save_settings(SETTINGS)
        return SETTINGS

    def list_plugin_items(self, plugin_id):
        return plugin_manager.list_items(plugin_id)

    def activate_plugin_item(self, plugin_id, item_id):
        result = plugin_manager.activate_item(plugin_id, item_id)
        if isinstance(result, dict) and result.get("ok") and SETTINGS.get("launch_system_with_osm", True):
            _maybe_launch_osm()
        return result

    # ---------------- macros ----------------
    def list_macro_items(self):
        builtin = [
            {"type": "builtin", "id": "close_others", "name": "Close all other programs"},
        ]
        shell_ps1 = BASE_DIR / "MakeUnmakeShell.ps1"
        if shell_ps1.exists():
            builtin.append({
                "type": "builtin", "id": "toggle_default_shell",
                "name": "Make / Unmake Meridian The Default Shell",
            })
        cdb = BASE_DIR / "CyberDeckBrowser.exe"
        if cdb.exists():
            builtin.append({
                "type": "builtin", "id": "cdb_default_browser",
                "name": "Make CyberDeckBrowser the default browser",
            })
        mx = BASE_DIR / "Meridian Explorer.exe"
        if mx.exists():
            installed = explorer_shell.context_menu_installed()
            builtin.append({
                "type": "builtin", "id": "mx_context_menu",
                "name": ("Remove 'Open in Meridian Explorer' from context menus"
                         if installed else
                         "Add 'Open in Meridian Explorer' to context menus"),
            })
            builtin.append({
                "type": "builtin", "id": "mx_default_handler",
                "name": "Make Meridian Explorer the default folder handler",
            })
            builtin.append({
                "type": "builtin", "id": "mx_restore_handler",
                "name": "Restore Windows Explorer as default folder handler",
            })
        fb_trampoline = BASE_DIR / "Meridian FileBrowse Shell Handler.exe"
        if fb_trampoline.exists():
            fb_installed = explorer_shell.filebrowse_default_handler_installed()
            builtin.append({
                "type": "builtin", "id": "fb_default_shell_browser",
                "name": ("Unmake Meridian FileBrowse the default shell browser"
                         if fb_installed else
                         "Make Meridian FileBrowse the default shell browser"),
            })
        nb_trampoline = BASE_DIR / "Meridian NetBrowse Shell Handler.exe"
        if nb_trampoline.exists():
            builtin.append({
                "type": "builtin", "id": "nb_default_shell_browser",
                "name": "Make Meridian NetBrowse the default system web browser",
            })
        scripts = _with_icons(SETTINGS["sections"]["macros"]["items"])
        for s in scripts:
            s.setdefault("type", "bat")  # existing saved items predate .ps1 support
        return builtin + scripts

    def add_bat_to_macros(self):
        """Add a .bat or .ps1 macro script; kept the original method name
        since the frontend already calls it, just broadened what it
        accepts. Type is inferred from the extension."""
        paths = _open_file_dialog(SCRIPT_FILE_TYPES)
        items = SETTINGS["sections"]["macros"]["items"]
        for p in paths:
            if not any(it["path"] == p for it in items):
                script_type = "ps1" if p.lower().endswith(".ps1") else "bat"
                items.append({"type": script_type, "path": p, "name": store.display_name(p)})
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
        if macro_id == "toggle_default_shell":
            return self.run_ps1_file(str(BASE_DIR / "MakeUnmakeShell.ps1"))
        if macro_id == "cdb_default_browser":
            cdb = BASE_DIR / "CyberDeckBrowser.exe"
            if not cdb.exists():
                return {"ok": False, "error": "CyberDeckBrowser.exe not found."}
            try:
                subprocess.Popen([str(cdb), "--register-default-browser"], cwd=str(BASE_DIR))
                return {"ok": True, "message": ("Registered CyberDeckBrowser as a browser. "
                        "Windows may ask you to confirm it as the default in "
                        "Settings > Default apps.")}
            except Exception as e:
                return {"ok": False, "error": str(e)}
        if macro_id in ("mx_context_menu", "mx_default_handler", "mx_restore_handler"):
            mx = str(BASE_DIR / "Meridian Explorer.exe")
            if macro_id == "mx_context_menu":
                if explorer_shell.context_menu_installed():
                    ok, err = explorer_shell.remove_context_menu()
                    msg = "Removed 'Open in Meridian Explorer' from context menus."
                else:
                    ok, err = explorer_shell.add_context_menu(mx)
                    msg = "Added 'Open in Meridian Explorer' to folder/drive context menus."
            elif macro_id == "mx_default_handler":
                ok, err = explorer_shell.set_default_handler(mx)
                msg = ("Meridian Explorer is now the default folder handler. "
                       "(Browsing inside an already-open Windows Explorer window is unaffected.)")
            else:
                ok, err = explorer_shell.restore_default_handler()
                msg = "Windows Explorer is the default folder handler again."
            return {"ok": ok, "error": err, "message": msg if ok else None}
        if macro_id == "fb_default_shell_browser":
            fb_trampoline = BASE_DIR / "Meridian FileBrowse Shell Handler.exe"
            if not fb_trampoline.exists():
                return {"ok": False, "error": "Meridian FileBrowse Shell Handler.exe not found."}
            if explorer_shell.filebrowse_default_handler_installed():
                ok, err = explorer_shell.restore_filebrowse_default_handler()
                msg = "Windows Explorer is the default folder handler again."
            else:
                ok, err = explorer_shell.set_filebrowse_default_handler(str(fb_trampoline))
                msg = ("Folders now open through Meridian Launcher's Explorer section "
                       "(Meridian FileBrowse). If Meridian Launcher isn't running, opening "
                       "a folder launches it first.")
            return {"ok": ok, "error": err, "message": msg if ok else None}
        if macro_id == "nb_default_shell_browser":
            nb_trampoline = BASE_DIR / "Meridian NetBrowse Shell Handler.exe"
            if not nb_trampoline.exists():
                return {"ok": False, "error": "Meridian NetBrowse Shell Handler.exe not found."}
            ok, err = system_actions.register_netbrowse_default_browser(str(nb_trampoline))
            msg = ("Registered — links now route through Meridian Launcher's Browser section "
                   "(Meridian NetBrowse). Windows may ask you to confirm it as the default in "
                   "Settings > Default apps.")
            return {"ok": ok, "error": err, "message": msg if ok else None}
        return {"ok": False, "error": "Unknown macro"}

    def run_ps1_file(self, path):
        """Run any .ps1 macro (bundled or user-added) elevated. If even the
        per-process elevation attempt fails, the frontend offers restarting
        Meridian Launcher itself as administrator instead — see
        relaunch_as_admin below."""
        ok, err, needs_admin_relaunch = system_actions.launch_ps1_elevated(path)
        return {"ok": ok, "error": err, "needs_admin_relaunch": needs_admin_relaunch}

    def relaunch_as_admin(self):
        """Restart Meridian Launcher itself elevated (UAC prompt), then quit
        this non-elevated instance. Only called after a per-macro elevation
        attempt (run_ps1_file) has already failed."""
        try:
            import ctypes
            exe = sys.executable
            params = " ".join(f'"{a}"' for a in sys.argv[1:])
            result = ctypes.windll.shell32.ShellExecuteW(None, "runas", exe, params, str(BASE_DIR), 1)
            if result > 32:
                threading.Timer(0.3, lambda: os._exit(0)).start()
                return {"ok": True}
            return {"ok": False, "error": "Elevation was declined or failed."}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    # ---------------- web / files / system ----------------
    def open_web(self):
        ok, err = system_actions.open_default_browser()
    
        # Run the .bat file from the same directory as this Python script
        self._run_osm_batch()
    
        return {"ok": ok, "error": err}


    def open_files(self):
        ok, err = system_actions.open_this_pc()
    
        # Run the .bat file from the same directory as this Python script
        self._run_osm_batch()
    
        return {"ok": ok, "error": err}


    # Helper method (add this to your class)
    def _run_osm_batch(self):
        try:
            # Get the directory where the Python script is located
            script_dir = os.path.dirname(os.path.abspath(__file__))
            bat_path = os.path.join(script_dir, "osm.bat")   # Change name if different
        
            if os.path.exists(bat_path):
            # Run the batch file hidden (no window)
                subprocess.Popen(
                [bat_path],
                shell=True,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            else:
                print(f"Warning: {bat_path} not found")
        except Exception as e:
            print(f"Failed to run OSM batch: {e}")

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
        if ok and SETTINGS.get("launch_system_with_osm", True):
            _maybe_launch_osm()
        return {"ok": ok, "error": err}

    def system_task_manager(self):
        ok, err = system_actions.open_task_manager()
        if ok and SETTINGS.get("launch_system_with_osm", True):
            _maybe_launch_osm()
        return {"ok": ok, "error": err}

    def system_recycle_bin(self):
        ok, err = system_actions.open_recycle_bin()
        if ok and SETTINGS.get("launch_system_with_osm", True):
            _maybe_launch_osm()
        return {"ok": ok, "error": err}

    def system_uninstall_apps(self):
        ok, err = system_actions.open_uninstall_apps()
        if ok and SETTINGS.get("launch_system_with_osm", True):
            _maybe_launch_osm()
        return {"ok": ok, "error": err}

    def system_command_prompt(self):
        ok, err = system_actions.open_command_prompt()
        if ok and SETTINGS.get("launch_system_with_osm", True):
            _maybe_launch_osm()
        return {"ok": ok, "error": err}

    def system_powershell(self):
        ok, err = system_actions.open_powershell()
        if ok and SETTINGS.get("launch_system_with_osm", True):
            _maybe_launch_osm()
        return {"ok": ok, "error": err}

    def system_microsoft_store(self):
        ok, err = system_actions.open_microsoft_store()
        if ok and SETTINGS.get("launch_system_with_osm", True):
            _maybe_launch_osm()
        return {"ok": ok, "error": err}

    def system_windows_update(self):
        ok, err = system_actions.open_windows_update()
        if ok and SETTINGS.get("launch_system_with_osm", True):
            _maybe_launch_osm()
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
        if ok and SETTINGS.get("launch_system_with_osm", True):
            _maybe_launch_osm()
        return {"ok": ok, "error": err}

    # ---------------- Files section ----------------
    def launch_meridian_explorer(self):
        exe = BASE_DIR / "Meridian Explorer.exe"
        if not exe.exists():
            return {"ok": False, "error": "Meridian_Explorer.exe not found in the app folder."}
        ok, err = system_actions.launch_path(str(exe))
        return {"ok": ok, "error": err}

    def open_desktop_entry(self, path, is_dir):
        """Called when the user activates a Desktop-section entry. Files
        keep going through the normal launch path; folders are routed:
        Explorer section visible -> tell the frontend to switch to it and
        load Meridian Explorer boxed into that section's box; Explorer
        section hidden -> open standalone Meridian Explorer (windowed, not
        fullscreen); Meridian Explorer missing -> fall back to Windows
        Explorer."""
        if not is_dir:
            ok, err = system_actions.launch_path(path)
            return {"ok": ok, "error": err, "route": "launched"}

        if SETTINGS.get("explorer_section_enabled", False):
            return {"ok": True, "error": None, "route": "explorer_section", "path": path}

        exe = BASE_DIR / "Meridian Explorer.exe"
        if exe.exists():
            ok, err = system_actions.launch_path(str(exe), args=[path])
            return {"ok": ok, "error": err, "route": "meridian_explorer"}
        ok, err = system_actions.open_folder(path)
        return {"ok": ok, "error": err, "route": "windows_explorer"}

    def load_explorer_box(self, path, x, y, w, h):
        """Launch (or relaunch, for a new path) Meridian FileBrowse — the
        Explorer-section-embedded fork of Meridian Explorer, kept in its
        own separate source files (Meridian_FileBrowse/) — sized/positioned
        via its --box=X,Y,W,H arg to sit inside the Explorer section's
        list-frame box. Never OS fullscreen. Meridian Launcher's own
        controller bindings are suspended for the duration; a background
        watcher notices when the user exits Meridian FileBrowse (its
        Start/Escape "Exit Program" action) and hands focus + controls
        back to Meridian Launcher automatically."""
        global _explorer_box_proc
        exe = BASE_DIR / "Meridian FileBrowse.exe"
        if not exe.exists():
            return {"ok": False, "error": "Meridian FileBrowse.exe not found in the app folder."}
        self.unload_explorer_box()
        try:
            args = [str(exe), path, f"--box={int(x)},{int(y)},{int(w)},{int(h)}"]
            _explorer_box_proc = subprocess.Popen(
                args, cwd=str(BASE_DIR),
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            suspend_main_controls(True)
            threading.Thread(target=_watch_explorer_box_exit, args=(_explorer_box_proc,), daemon=True).start()
            return {"ok": True, "error": None}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def unload_explorer_box(self):
        """Terminate the boxed Meridian Explorer process, if any, so it
        doesn't keep running in the background once the user leaves the
        Explorer section, and hand Meridian Launcher's own controls back."""
        global _explorer_box_proc
        if _explorer_box_proc is not None:
            try:
                if _explorer_box_proc.poll() is None:
                    _explorer_box_proc.terminate()
            except Exception:
                pass
            _explorer_box_proc = None
        suspend_main_controls(False)
        return {"ok": True, "error": None}

    # ---------------- Web section ----------------
    def open_web_link(self, url):
        """Called when the user activates an internally-launched URL (a
        Web-section shortcut, etc). Routes it: Browser section visible ->
        tell the frontend to switch to it and load Meridian NetBrowse boxed
        into that section's box; Browser section hidden -> open standalone
        CyberDeckBrowser; CyberDeckBrowser missing -> system default
        browser; that failing too -> caller shows a toast and moves on."""
        if SETTINGS.get("browser_section_enabled", False):
            return {"ok": True, "error": None, "route": "browser_section", "url": url}

        cdb = BASE_DIR / "CyberDeckBrowser.exe"
        if cdb.exists():
            args = [WINDOW_MODE_REQUEST_FLAG] + ([url] if url else [])
            ok, err = system_actions.launch_path(str(cdb), args=args)
            return {"ok": ok, "error": err, "route": "cyberdeck"}

        ok, err = system_actions.open_default_browser(url or "https://www.google.com")
        return {"ok": ok, "error": err, "route": "system_browser"}

    def load_browser_box(self, url, x, y, w, h):
        """Launch (or relaunch, for a new URL) CyberDeckBrowser boxed into
        the Browser section — sized/positioned via its --box=X,Y,W,H arg
        to sit inside the section's list-frame box, never OS fullscreen.
        Same controller suspend/watcher pattern as Meridian FileBrowse.
        (Meridian NetBrowse used to be a separate app for this — merged
        back into CyberDeckBrowser itself, since running two full
        QtWebEngine/Chromium bundles side by side was the single biggest
        contributor to the suite's compiled size.)"""
        global _browser_box_proc
        exe = BASE_DIR / "CyberDeckBrowser.exe"
        if not exe.exists():
            return {"ok": False, "error": "CyberDeckBrowser.exe not found in the app folder."}
        self.unload_browser_box()
        try:
            args = [str(exe), f"--box={int(x)},{int(y)},{int(w)},{int(h)}", "--notify-exit=browser"] + ([url] if url else [])
            _browser_box_proc = subprocess.Popen(
                args, cwd=str(BASE_DIR),
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            suspend_main_controls(True)
            threading.Thread(target=_watch_browser_box_exit, args=(_browser_box_proc,), daemon=True).start()
            return {"ok": True, "error": None}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def unload_browser_box(self):
        """Terminate the boxed Meridian NetBrowse process, if any, so it
        doesn't keep running in the background once the user leaves the
        Browser section, and hand Meridian Launcher's own controls back."""
        global _browser_box_proc
        if _browser_box_proc is not None:
            try:
                if _browser_box_proc.poll() is None:
                    _browser_box_proc.terminate()
            except Exception:
                pass
            _browser_box_proc = None
        suspend_main_controls(False)
        return {"ok": True, "error": None}

    def launch_cyberdeck(self, url=None):
        """Launch CyberDeckBrowser, optionally straight to a URL (used by
        the Web section's user-added shortcuts). Assumes CyberDeckBrowser
        accepts a bare URL as a command-line argument the same way most
        Chromium-based browsers do — worth confirming against the actual
        CyberDeckBrowser build if shortcuts don't land on the right page."""
        exe = BASE_DIR / "CyberDeckBrowser.exe"
        if not exe.exists():
            return {"ok": False, "error": "CyberDeckBrowser.exe not found in the app folder."}
        args = [WINDOW_MODE_REQUEST_FLAG] + ([url] if url else [])
        ok, err = system_actions.launch_path(str(exe), args=args)
        return {"ok": ok, "error": err}

    def add_web_shortcut(self, url):
        from urllib.parse import urlparse
        label = urlparse(url).netloc or url
        label = label[4:] if label.startswith("www.") else label
        shortcuts = SETTINGS.setdefault("web_shortcuts", [])
        if not any(s["url"] == url for s in shortcuts):
            shortcuts.append({"url": url, "label": label})
            store.save_settings(SETTINGS)
        return SETTINGS

    def remove_web_shortcut(self, url):
        SETTINGS["web_shortcuts"] = [s for s in SETTINGS.get("web_shortcuts", []) if s["url"] != url]
        store.save_settings(SETTINGS)
        return SETTINGS

    def quit_app(self):
        os._exit(0)

    def minimize_launcher(self):
        """Start menu's "Minimize Launcher" option."""
        try:
            webview.windows[0].minimize()
            return {"ok": True, "error": None}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def toggle_onscreenmenu(self):
        """Start menu's "Launch/Close onscreenmenu" option: if
        onscreenmenu.exe is already running, terminate it; otherwise
        launch it via osm.bat from the local folder (never both — no
        double-launching)."""
        try:
            if system_actions.is_process_running("onscreenmenu.exe"):
                ok, err = system_actions.kill_process("onscreenmenu.exe")
                return {"ok": ok, "error": err}
            bat = BASE_DIR / "osm.bat"
            if not bat.exists():
                return {"ok": False, "error": "osm.bat not found in the app folder."}
            subprocess.Popen(
                ["cmd.exe", "/c", str(bat)], cwd=str(BASE_DIR),
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            return {"ok": True, "error": None}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    # ---------------- appearance ----------------
    # Background & overlay are now per-theme (keyed by the active layout),
    # so each theme can carry its own look. An unset theme falls back to
    # that theme's rendered placeholder (theme_assets). Backgrounds accept
    # animated .gif too — the frontend shows them on a CSS layer that
    # animates, unlike the keyed overlay canvas.

    def _layout_key(self):
        return SETTINGS.get("layout", "dawning_horizon")

    def theme_asset_urls(self):
        """Placeholder background+overlay URLs for the current theme, so the
        frontend has something to show when the user hasn't picked one."""
        assets = str(store.ASSETS_DIR)
        layout = self._layout_key()
        bg = theme_assets.placeholder_background(assets, "launcher", layout)
        ov = theme_assets.placeholder_overlay(assets, "launcher", layout)
        return {
            "background": media_url(bg) if bg else None,
            "overlay": media_url(ov) if ov else None,
        }

    def set_background(self):
        # IMAGE_FILE_TYPES is a tuple of pywebview filter STRINGS; build the
        # background filter the same way (including .gif for animated
        # backgrounds). Concatenating a list of tuples here raises TypeError
        # and the dialog never opens.
        paths = _open_file_dialog(BACKGROUND_FILE_TYPES)
        if paths:
            SETTINGS.setdefault("background_by_theme", {})[self._layout_key()] = paths[0]
            store.save_settings(SETTINGS)
        return SETTINGS

    def set_background_from_path(self, path):
        """Same as set_background(), but for a path the person already
        picked in-app (the Photos section's Start-button "Set as
        Background" option) rather than a fresh file-picker dialog."""
        if not path or not os.path.isfile(path):
            return None
        SETTINGS.setdefault("background_by_theme", {})[self._layout_key()] = path
        store.save_settings(SETTINGS)
        return SETTINGS

    def edit_photo(self, path):
        """Photos section's Start-button "Edit" option: opens the photo
        with whatever program Windows has associated with the "edit"
        action for that file type (usually Paint for images, but this no
        longer hard-requires mspaint.exe specifically — some Windows
        installs don't have it on PATH, or replace it with the Photos
        app's own editor), and brings up the on-screen menu (same pattern
        every other launch in this app follows) since editing needs
        on-screen typing/menu access same as anything else."""
        if not path or not os.path.isfile(path):
            return {"ok": False, "error": "That file no longer exists."}
        try:
            # ShellExecute's "edit" verb - resolves to whatever program is
            # actually registered for editing this file type, same concept
            # as right-click > Edit in Windows Explorer.
            os.startfile(path, "edit")
        except OSError:
            try:
                # No "edit" verb registered for this file type - fall back
                # to just opening it with the plain default program.
                os.startfile(path)
            except Exception as e:
                return {"ok": False, "error": str(e)}
        except Exception as e:
            return {"ok": False, "error": str(e)}
        self._run_osm_batch()
        return {"ok": True, "error": None}

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

    def set_fullscreen_helper_enabled(self, enabled):
        SETTINGS["fullscreen_helper_enabled"] = bool(enabled)
        store.save_settings(SETTINGS)
        return SETTINGS

    def set_auto_shuffle_songs(self, enabled):
        SETTINGS["auto_shuffle_songs"] = bool(enabled)
        store.save_settings(SETTINGS)
        return SETTINGS

    def set_window_mode(self, mode):
        SETTINGS["window_mode"] = mode
        store.save_settings(SETTINGS)
        try:
            win = webview.windows[0]
            is_exclusive = getattr(win, "_meridian_exclusive_fs", False)
            if mode == "exclusive_fullscreen":
                if not is_exclusive:
                    win.toggle_fullscreen()  # true OS-level fullscreen
                    win._meridian_exclusive_fs = True
                win._meridian_fullscreen = True
            elif mode in ("windowed_fullscreen", "kiosk"):
                if is_exclusive:
                    win.toggle_fullscreen()  # drop out of exclusive fullscreen first
                    win._meridian_exclusive_fs = False
                # Borderless windowed fullscreen instead of OS-exclusive
                # fullscreen: move the frameless window to (0, 0) to cover
                # the screen. The frame itself can't be added/removed at
                # runtime (pywebview limitation) — see _apply_kiosk_disable.
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

    # ---------------- open-programs bar (taskbar replacement) ----------------

    def list_open_tasks(self):
        return tasks_win.list_open_tasks()

    def focus_task(self, hwnd):
        ok = tasks_win.focus_task(hwnd)
        if ok and SETTINGS.get("launch_system_with_osm", True):
            _maybe_launch_osm()
        return {"ok": ok}

    def close_task(self, hwnd):
        return {"ok": tasks_win.close_task(hwnd)}

    def set_prefer_xinput(self, enabled):
        """Switch the input backend live. XInput is the proven path;
        GameInput adds Guide-button reporting. Restarts the listener so the
        change takes effect without relaunching the app."""
        SETTINGS["prefer_xinput"] = bool(enabled)
        store.save_settings(SETTINGS)
        restart_controller()
        return SETTINGS

    def set_input_backend(self, backend):
        """Settings > Controls "Input backend" cycle button: xinput
        (default) -> gameinput -> directinput -> sdl3 -> auto -> xinput...
        Restarts the listener so the change takes effect without
        relaunching. XInput is the default because it's the plain, stable,
        fully-public Win32 API and correctly reports every button/trigger/
        stick; GameInput's vtable-slot probing has only ever reliably
        decoded buttons, not sticks/triggers, across multiple independent
        reports - that's a real bug in that approach, not a one-off local
        issue, so it's opt-in now rather than the default."""
        if backend not in ("xinput", "gameinput", "directinput", "sdl3", "auto"):
            return SETTINGS
        SETTINGS["input_backend"] = backend
        # Keep the older boolean in sync for anything still reading it.
        SETTINGS["prefer_xinput"] = (backend == "xinput")
        store.save_settings(SETTINGS)
        restart_controller()
        return SETTINGS

    def controller_debug(self):
        """Deep diagnostics for the Settings controller debugger: which
        backend is live, what GameInput is doing poll-by-poll, and the raw
        state the pad is reporting right now."""
        import gameinput_api
        out = {
            "input_backend": SETTINGS.get("input_backend", "xinput"),
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

    def set_icon_size(self, size):
        if size not in ("small", "medium", "large", "xl"):
            return SETTINGS
        SETTINGS["icon_size"] = size
        store.save_settings(SETTINGS)
        return SETTINGS

    def meridian_explorer_available(self):
        """Whether Meridian Explorer.exe sits next to this app — the folder-
        routing toggle is only meaningful when it does."""
        return (BASE_DIR / "Meridian Explorer.exe").exists()

    def set_route_folders_to_meridian_explorer(self, enabled):
        # Only allow enabling when the Explorer exe is actually present.
        if enabled and not (BASE_DIR / "Meridian Explorer.exe").exists():
            SETTINGS["route_folders_to_meridian_explorer"] = False
            store.save_settings(SETTINGS)
            return SETTINGS
        SETTINGS["route_folders_to_meridian_explorer"] = bool(enabled)
        store.save_settings(SETTINGS)
        return SETTINGS

    def set_foreground_trigger(self, mode):
        if mode not in ("start_select", "xbox", "off"):
            return SETTINGS
        SETTINGS["foreground_trigger"] = mode
        store.save_settings(SETTINGS)
        return SETTINGS

    def set_nav_speed_fast(self, fast):
        """Frontend toggles this on while the Settings list is focused so its
        cursor moves ~1.3x faster than normal navigation."""
        _NAV_COOLDOWN_SCALE[0] = (1.0 / 1.3) if fast else 1.0
        return True

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

    # ---------------- kiosk mode: exit paths ----------------
    def disable_kiosk_via_code(self):
        """Called by the frontend once it detects the secret controller/
        keyboard unlock sequence. Only does anything if kiosk mode is
        actually on right now."""
        if SETTINGS.get("window_mode") != "kiosk":
            return {"ok": False}
        _apply_kiosk_disable()
        return {"ok": True}

    # ---------------- per-section / system "launch with onscreenmenu" toggles ----------------
    def set_section_osm(self, section_id, enabled):
        sec = _section_store(section_id)
        if sec is not None:
            sec["launch_with_osm"] = bool(enabled)
            store.save_settings(SETTINGS)
        return SETTINGS

    def set_system_osm(self, enabled):
        SETTINGS["launch_system_with_osm"] = bool(enabled)
        store.save_settings(SETTINGS)
        return SETTINGS

    # ---------------- factory reset ----------------
    def factory_reset(self):
        fresh = store.default_settings()
        SETTINGS.clear()
        SETTINGS.update(fresh)
        store.save_settings(SETTINGS)
        return SETTINGS

    # ---------------- Games section: Game Library entry ----------------
    def launch_game_library(self):
        exe = BASE_DIR / "Meridian Game Library.exe"
        if not exe.exists():
            return {"ok": False, "error": "Meridian Game Library.exe not found in the app folder."}
        ok, err = system_actions.launch_path(str(exe), args=[WINDOW_MODE_REQUEST_FLAG])
        return {"ok": ok, "error": err}

    # ---------------- settings: app data folder ----------------
    def open_app_data_folder(self):
        """Opens %LOCALAPPDATA%\\Meridian Launcher\\ in Explorer, then makes
        sure onscreenmenu is running (launched if it wasn't already) so a
        controller can be used to navigate the folder."""
        ok, err = _open_folder_routed(str(store.DATA_DIR))
        if ok:
            _maybe_launch_onscreenmenu()
        return {"ok": ok, "error": err}

    # ---------------- settings: updates ----------------
    def get_version(self):
        return {"version": CURRENT_VERSION}

    def check_for_updates(self):
        """Manual "Check for Updates" button in Settings — same check as
        the silent one at boot, just triggered on demand and always
        reported back to the UI (including "you're up to date")."""
        return updater.check_for_update(CURRENT_VERSION)

    def start_update(self, download_url):
        """Downloads the .exe installer and launches it, then quits the app
        so the installer isn't fighting a running/locked
        MeridianLauncher.exe."""
        ok, err = updater.download_and_run_installer(download_url)
        if ok:
            threading.Timer(0.6, lambda: os._exit(0)).start()
        return {"ok": ok, "error": err}
    



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



# [action_name, timestamp] of the most recent controller action to reach the
# app — the settings debugger uses it to prove input is (or isn't) arriving.
_LAST_CONTROLLER_ACTION = [None, 0.0]

# True while a boxed sub-app (Meridian FileBrowse / Meridian NetBrowse) has
# its own window focused and its own controller polling active — Meridian
# Launcher's own listener still runs (so the quit combo always works as a
# safety net) but stops forwarding normal navigation actions/raw buttons to
# the frontend, so the two don't fight over the same physical controller.
_controller_suspended_for_plugin = False


def suspend_main_controls(suspended=True):
    global _controller_suspended_for_plugin
    _controller_suspended_for_plugin = bool(suspended)


def _watch_explorer_box_exit(proc):
    """Runs in a background thread for as long as a boxed Meridian
    FileBrowse process lives. When the user picks its "Exit Program"
    action (Start/Escape), the process simply exits; this notices and
    tells the frontend to move the section selector back to the Sections
    bar, then restores Meridian Launcher's own controls. If the user
    instead navigates Meridian Launcher away from the Explorer section
    first, unload_explorer_box() will already have replaced
    _explorer_box_proc / cleared the suspend flag, so this becomes a
    no-op once it notices proc is no longer the active one."""
    proc.wait()
    if _explorer_box_proc is not proc:
        return  # already unloaded via normal navigation; nothing to do
    suspend_main_controls(False)
    try:
        webview.windows[0].evaluate_js(
            "window.onEmbeddedPluginExited && window.onEmbeddedPluginExited('explorer')"
        )
    except Exception:
        pass


def _watch_browser_box_exit(proc):
    """Same as _watch_explorer_box_exit, for the boxed Meridian NetBrowse
    process in the Browser section."""
    proc.wait()
    if _browser_box_proc is not proc:
        return
    suspend_main_controls(False)
    try:
        webview.windows[0].evaluate_js(
            "window.onEmbeddedPluginExited && window.onEmbeddedPluginExited('browser')"
        )
    except Exception:
        pass


def _watch_plugin_webapp_exit(plugin_id, proc):
    """Same idea for a boxed webapp plugin (Telegram/Discord/Messenger/
    Snapchat/etc): notices when its "Exit Program" menu action closes the
    window and hands focus + controls back to Meridian Launcher."""
    proc.wait()
    if _plugin_webapp_procs.get(plugin_id) is not proc:
        return  # already unloaded via normal navigation; nothing to do
    _plugin_webapp_procs.pop(plugin_id, None)
    suspend_main_controls(False)
    try:
        escaped = plugin_id.replace("'", "\\'")
        webview.windows[0].evaluate_js(
            f"window.onEmbeddedPluginExited && window.onEmbeddedPluginExited('{escaped}')"
        )
    except Exception:
        pass


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
    if _controller_suspended_for_plugin:
        return
    # record it for the settings debugger before dispatching
    _LAST_CONTROLLER_ACTION[0] = action_name
    _LAST_CONTROLLER_ACTION[1] = time.time()
    try:
        webview.windows[0].evaluate_js(f"window.handleControllerInput && window.handleControllerInput('{action_name}')")
    except Exception:
        pass


def _controller_any():
    if _controller_suspended_for_plugin:
        return
    try:
        webview.windows[0].evaluate_js("window.handleControllerAny && window.handleControllerAny()")
    except Exception:
        pass


def _controller_raw_button(name):
    """Forwards raw DPAD/A/B rising edges to the frontend, independent of
    whatever the user has confirm/back remapped to — used only to watch for
    the kiosk-mode secret unlock sequence."""
    if _controller_suspended_for_plugin:
        return
    try:
        webview.windows[0].evaluate_js(f"window.handleRawControllerButton && window.handleRawControllerButton('{name}')")
    except Exception:
        pass


def _on_y_hold_complete():
    """Fired after the controller's Y button has been held continuously for
    45 seconds — one of kiosk mode's three exit paths."""
    if SETTINGS.get("window_mode") != "kiosk":
        return
    _apply_kiosk_disable()
    try:
        webview.windows[0].evaluate_js("window.onKioskDisabledExternally && window.onKioskDisabledExternally()")
    except Exception:
        pass


# Settings navigation runs 1.3x faster than the global cooldown; the
# frontend flips this to 0.77 while the Settings section is focused and back
# to 1.0 elsewhere, via set_nav_speed_fast().
_NAV_COOLDOWN_SCALE = [1.0]


def _open_folder_routed(path):
    """Open a folder, honoring the "Open folders in Meridian Explorer"
    setting: routed to Meridian Explorer.exe (sitting next to this exe in
    the shared DskoTech folder) with the path as its argument, or the
    regular Windows Explorer open when the setting is off or the exe is
    missing. Creates the folder first, matching open_folder's behavior."""
    try:
        os.makedirs(path, exist_ok=True)
    except Exception as e:
        return False, str(e)
    if SETTINGS.get("route_folders_to_meridian_explorer"):
        exe = BASE_DIR / "Meridian Explorer.exe"
        if exe.exists():
            try:
                subprocess.Popen([str(exe), str(path)], cwd=str(BASE_DIR))
                return True, None
            except Exception:
                pass  # fall through to the normal Explorer open
    return system_actions.open_folder(path)


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
        input_backend=SETTINGS.get("input_backend", "xinput"),
        cooldown_scale_getter=lambda: _NAV_COOLDOWN_SCALE[0],
        on_raw_button=_controller_raw_button,
        on_y_hold_complete=_on_y_hold_complete,
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


def _check_for_update_at_boot(window):
    """Runs once the webview window exists (see the func= passed to
    webview.start below), in its own thread so the network call never
    blocks startup. Silent on failure or when already up to date — only
    pushes something to the UI when there's an actual update to offer."""
    if SETTINGS.get("window_mode") == "exclusive_fullscreen":
        try:
            window.toggle_fullscreen()
            window._meridian_exclusive_fs = True
        except Exception:
            pass
    try:
        result = updater.check_for_update(CURRENT_VERSION)
    except Exception:
        return
    if not result.get("available"):
        return
    try:
        payload = json.dumps({
            "current": result.get("current"),
            "latest": result.get("latest"),
            "download_url": result.get("download_url"),
            "notes": result.get("notes", ""),
        })
        window.evaluate_js(f"window.onUpdateAvailable && window.onUpdateAvailable({payload})")
    except Exception:
        pass


def main():
    width, height = detect_screen_size()
    mode = SETTINGS.get("window_mode", "windowed_fullscreen")
    # Borderless (windowed) fullscreen: a frameless window sized and
    # positioned to exactly cover the screen. Exclusive fullscreen instead
    # requests a real OS display-mode fullscreen switch via toggle_fullscreen()
    # once the window exists (can't be requested at creation time), see below.
    borderless_fullscreen = mode in ("windowed_fullscreen", "kiosk")
    frameless = borderless_fullscreen

    api = Api()
    window = webview.create_window(
        APP_TITLE,
        "frontend/index.html",
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

    start_controller()
    start_background_precache()
    webview.start(
        _check_for_update_at_boot, window,
        debug=False, gui="edgechromium",
    )


if __name__ == "__main__":
    main()
