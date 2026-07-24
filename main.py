"""
MeridianLauncher — a Windows media hub / app launcher front-end.

Sections: Music, Photos, Videos, Apps, Games, Emulators, Chat, Streaming,
Web, Files, System, Macros, plus user-defined custom sections. Navigable by
keyboard, mouse, or game controller (XInput).
"""

import ctypes
from ctypes import wintypes
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
    _DLG_SAVE = webview.FileDialog.SAVE
except AttributeError:  # pywebview < 5.x
    _DLG_OPEN = getattr(webview, "OPEN_DIALOG")
    _DLG_FOLDER = getattr(webview, "FOLDER_DIALOG")
    _DLG_SAVE = getattr(webview, "SAVE_DIALOG")

import store
import backup_restore
import audio_devices
import phone_type_server
import task_manager_server
import display_audio_server
import network_pairing_server
import desktop_refocus_watcher
import system_actions
import tasks_win
import explorer_shell
import user_themes
import theme_assets
import updater
import plugin_manager
import addon_settings
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
    import win32process
except ImportError:
    win32gui = None
    win32con = None
    win32ui = None
    win32api = None
    win32process = None

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


def _unblock_all_files_in(root_dir):
    """Internalized equivalent of:
        Get-ChildItem -Path <root_dir> -Recurse -Force | Unblock-File
    Removes the NTFS "Zone.Identifier" alternate data stream from every
    file under root_dir - the "Mark of the Web" Windows attaches to
    files that arrived via a browser download or an extracted zip,
    which is what makes Windows show a "this file came from another
    computer, are you sure?" SmartScreen prompt, and can silently block
    script/DLL loading in some contexts. A fresh install (downloaded as
    a zip, then extracted) has this on every single file, which is
    exactly the scenario this exists to clean up once, automatically,
    rather than needing everyone to know to run the PowerShell one-
    liner by hand.

    Deleting an NTFS alternate data stream is just deleting a file whose
    path happens to be "realpath:StreamName" - no special API needed,
    a plain os.remove() on that colon-suffixed path does it. Silently
    skips anything without that stream (the overwhelming majority of
    files, and the only realistic case: nothing to unblock) or that
    can't be touched for permission reasons - this is a nice-to-have
    cleanup pass, not something that should ever block startup or
    surface an error over a single file it couldn't reach."""
    if not root_dir or not os.path.isdir(root_dir):
        return
    for dirpath, _dirnames, filenames in os.walk(root_dir):
        for name in filenames:
            try:
                os.remove(os.path.join(dirpath, name) + ":Zone.Identifier")
            except OSError:
                pass  # no ADS present - the common case - or inaccessible


def _run_first_boot_unblock_if_needed():
    """Runs _unblock_all_files_in(BASE_DIR) exactly once per install,
    tracked via a SETTINGS flag so it doesn't re-sweep the whole folder
    on every single launch. On its own daemon thread - this has nothing
    to do with getting the window on screen, so it shouldn't delay that
    even by the fraction of a second a few hundred files might take."""
    if SETTINGS.get("_first_boot_unblock_done"):
        return
    SETTINGS["_first_boot_unblock_done"] = True
    store.save_settings(SETTINGS)

    def _sweep():
        try:
            _unblock_all_files_in(str(BASE_DIR))
        except Exception:
            pass

    threading.Thread(target=_sweep, daemon=True).start()


_run_first_boot_unblock_if_needed()

_browser_box_proc = None  # Popen handle for the boxed (non-fullscreen) Meridian NetBrowse instance, if any
_plugin_webapp_procs = {}  # plugin_id -> Popen handle, for "webapp"-type plugins (Telegram/Discord/etc)


def _is_builtin_section_visible(section_id):
    """Whether a built-in section is currently shown in the Sections bar -
    used to auto-disable any "addon" plug-on targeting it (see
    list_section_options). Two separate mechanisms exist for this across
    different built-in sections and both need checking:

      - Desktop/Browser: dedicated "*_section_enabled" settings,
        off by default (opt-in sections).
      - Everything else (Music/Photos/.../Chat): on by default, hideable
        via the general "hidden_builtin_sections" list instead.
    """
    special_flags = {
        "desktop": "desktop_section_enabled",
        "browser": "browser_section_enabled",
    }
    if section_id in special_flags:
        return bool(SETTINGS.get(special_flags[section_id], False))
    return section_id not in set(SETTINGS.get("hidden_builtin_sections", []))


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
        if info.get("type") in ("webapp", "option", "addon"):
            entry["url"] = info.get("url", "")
        if info.get("type") in ("option", "addon"):
            entry["section"] = info.get("section", "chat")
        merged[pid] = entry
    SETTINGS["plugins"] = merged
    store.save_settings(SETTINGS)
    return discovered


def _sync_phone_type_plugin_manifest(port):
    """Type from Phone's plugin.json hardcodes DEFAULT_PORT (58734) since
    a static manifest can't know a dynamically-chosen port ahead of time.
    That's normally exactly right - but on the rare machine where that
    port's already taken, phone_type_server.start_server() falls back to
    an OS-assigned one, and this keeps the addon's boxed URL pointing at
    wherever the server actually ended up instead of a dead port."""
    manifest_path = BASE_DIR / "Plugins" / "TypeFromPhone" / "plugin.json"
    if not manifest_path.exists() or not port:
        return
    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
        wanted_url = f"http://127.0.0.1:{port}/display"
        if data.get("url") != wanted_url:
            data["url"] = wanted_url
            manifest_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    except Exception:
        pass


def _sync_task_manager_plugin_manifest(port):
    """Same self-heal as the other plug-on manifests here, for the Task
    Manager plug-on's own fixed-port manifest."""
    manifest_path = BASE_DIR / "Plugins" / "MeridianTaskManager" / "plugin.json"
    if not manifest_path.exists() or not port:
        return
    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
        wanted_url = f"http://127.0.0.1:{port}/"
        if data.get("url") != wanted_url:
            data["url"] = wanted_url
            manifest_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    except Exception:
        pass


def _sync_display_audio_plugin_manifest(port):
    """Same self-heal as the other plug-on manifests above."""
    manifest_path = BASE_DIR / "Plugins" / "DisplayAudio" / "plugin.json"
    if not manifest_path.exists() or not port:
        return
    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
        wanted_url = f"http://127.0.0.1:{port}/"
        if data.get("url") != wanted_url:
            data["url"] = wanted_url
            manifest_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    except Exception:
        pass


def _sync_network_pairing_plugin_manifest(port):
    """Same self-heal as the other plug-on manifests above."""
    manifest_path = BASE_DIR / "Plugins" / "NetworkPairing" / "plugin.json"
    if not manifest_path.exists() or not port:
        return
    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
        wanted_url = f"http://127.0.0.1:{port}/"
        if data.get("url") != wanted_url:
            data["url"] = wanted_url
            manifest_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    except Exception:
        pass


def _start_plugon_server(module, sync_fn, name):
    """Each plug-on server's start_server() is a module-level call that
    runs unconditionally at Launcher startup - an uncaught exception here
    (a genuinely missing dependency in a compiled build is exactly the
    class of bug that's bitten this before - see audio_devices.py's own
    pycaw import fix) would crash Launcher itself before it ever gets to
    show a window. Wrapping each one independently also means one
    plug-on's server failing to start doesn't stop the other three from
    starting - a boxed webapp pointed at a dead server still fails
    (nothing can serve its page), but that failure is contained to that
    one plug-on instead of taking down Launcher or its siblings."""
    try:
        status = module.start_server()
        sync_fn(status.get("port"))
        return status
    except Exception as e:
        try:
            crash_dir = Path(os.environ.get("LOCALAPPDATA", os.path.expanduser("~"))) / "Meridian Launcher"
            crash_dir.mkdir(parents=True, exist_ok=True)
            (crash_dir / "plugon_server_startup_errors.txt").open("a", encoding="utf-8").write(
                f"{name}: {type(e).__name__}: {e}\n"
            )
        except Exception:
            pass
        return {"port": None}


# Deliberately NOT started here anymore - see _ensure_plugon_server_started()
# below, called lazily from load_plugin_webapp_box() only when one of
# these plugins is actually opened. Starting all four unconditionally at
# every Launcher boot (the original approach) meant four background HTTP
# servers running for the entire session even if someone never opens a
# single one of these plug-ons.
_LAZY_PLUGIN_SERVERS = {
    "type_from_phone": (phone_type_server, "_sync_phone_type_plugin_manifest"),
    "meridian_task_manager": (task_manager_server, "_sync_task_manager_plugin_manifest"),
    "display_audio_settings": (display_audio_server, "_sync_display_audio_plugin_manifest"),
    "network_pairing": (network_pairing_server, "_sync_network_pairing_plugin_manifest"),
}


def _ensure_plugon_server_started(plugin_id):
    """Starts the given plug-on's local server on first use (idempotent -
    each module's own start_server() is a no-op if already running), then
    re-syncs its plugin.json in case a fixed port had to fall back, and
    re-scans plugins so the freshly-synced URL is what gets read right
    after this returns."""
    entry = _LAZY_PLUGIN_SERVERS.get(plugin_id)
    if not entry:
        return
    module, sync_fn_name = entry
    sync_fn = globals()[sync_fn_name]
    _start_plugon_server(module, sync_fn, plugin_id)
    _rescan_plugins()

_rescan_plugins()

desktop_refocus_watcher.start()


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


def _entries_to_response(kind, path_to_entry, mtimes=None):
    """Turn cached/raw entries (with a stashed thumb path) into the shape
    the frontend expects, generating fresh media-server tokens every call
    since TOKEN_MAP doesn't persist across runs."""
    mtimes = mtimes or {}
    items = []
    for path, entry in path_to_entry.items():
        e = dict(entry)
        thumb = e.pop("_thumb_path", None)
        e["thumbUrl"] = media_url(thumb) if thumb else None
        if kind == "photos":
            e["fullUrl"] = media_url(path)
        else:
            e["url"] = media_url(path)
        # Used by the Music section's "Recently Added" sort option (client
        # side, see sortMusicItems() in app.js) - harmless extra field for
        # photos/videos, which don't currently expose a sort menu.
        if path in mtimes:
            e["mtime"] = mtimes[path]
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


def _toggle_default_shell():
    """Internalized equivalent of MakeUnmakeShell.ps1: toggles
    HKCU\\...\\Winlogon's "Shell" value between MeridianLauncher.exe and
    removed (= Windows' own default explorer.exe shell). Returns
    (ok, error, message). Deliberately does NOT force an immediate sign-
    out the way the original interactive script's "press any key to sign
    out" prompt did - triggered from a menu click rather than a console
    script someone deliberately ran, an unprompted forced logout would
    be a much bigger surprise here; the message tells the frontend to
    show the "you'll need to sign out to apply this" note instead, and
    leaves actually doing that up to the person."""
    try:
        import winreg
    except ImportError:
        return False, "winreg unavailable (not Windows).", None
    key_path = r"Software\Microsoft\Windows NT\CurrentVersion\Winlogon"
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_ALL_ACCESS)
    except Exception as e:
        return False, str(e), None
    try:
        try:
            winreg.QueryValueEx(key, "Shell")
            had_value = True
        except FileNotFoundError:
            had_value = False

        if had_value:
            winreg.DeleteValue(key, "Shell")
            return True, None, "Reverted to the default Windows desktop shell. Sign out (or restart) to apply."
        else:
            exe_path = str(BASE_DIR / "MeridianLauncher.exe")
            if not os.path.exists(exe_path):
                return False, "MeridianLauncher.exe not found next to this installation.", None
            winreg.SetValueEx(key, "Shell", 0, winreg.REG_SZ, exe_path)
            return True, None, f"Custom shell set to {exe_path}. Sign out (or restart) to apply."
    except Exception as e:
        return False, str(e), None
    finally:
        winreg.CloseKey(key)


def _launch_onscreenmenu(window_mode="borderless-fullscreen"):
    """Internalized equivalent of osm.bat: launches onscreenmenu.exe
    from BASE_DIR, but only if it isn't already running (osm.bat's own
    behavior - see its former docstring: launching again while it's
    already open used to close it, which was surprising, so this
    deliberately does nothing instead of double-launching or toggling).
    Returns (ok, error)."""
    if system_actions.is_process_running("onscreenmenu.exe"):
        return True, None
    exe = BASE_DIR / "onscreenmenu.exe"
    if not exe.exists():
        return False, "onscreenmenu.exe not found in the app folder."
    try:
        subprocess.Popen(
            [str(exe), f"--window-mode={window_mode}"], cwd=str(BASE_DIR),
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        return True, None
    except Exception as e:
        return False, str(e)


def _maybe_launch_osm():
    """Best-effort: launches onscreenmenu.exe (if not already running)
    directly - no osm.bat involved. The toggle that triggers this
    defaults to on, so a failure here shouldn't spam the user with error
    toasts, hence best-effort rather than surfacing the (ok, error)."""
    try:
        _launch_onscreenmenu()
    except Exception:
        pass


def _maybe_launch_onscreenmenu():
    """Best-effort launch of onscreenmenu.exe, but only if it isn't
    already running - used after opening the app data folder so the
    on-screen menu companion is available to navigate it with a
    controller. _launch_onscreenmenu() already checks this itself, so
    this is now just a thin, clearly-named wrapper for that call site."""
    _maybe_launch_osm()


# Tracks the previous is_foreground() result so onscreenmenu.exe only gets
# closed once, on the rising edge of Meridian Launcher becoming the OS
# foreground window, rather than on every ~400ms poll from the frontend.
_WAS_FOREGROUND = False


def _close_onscreenmenu_if_running():
    """Best-effort close of the on-screen menu companion overlay. Used
    whenever something makes it redundant: Meridian Launcher itself
    regaining foreground, or CyberDeckBrowser/Meridian NetBrowse being
    opened (see launch_cyberdeck / launch web-browse section handling) -
    onscreenmenu is only meant to cover external, non-Meridian apps."""
    try:
        if system_actions.is_process_running("onscreenmenu.exe"):
            system_actions.kill_process("onscreenmenu.exe")
    except Exception:
        pass


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
    return _entries_to_response(kind, fresh_items, current_mtimes)


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


def _controller_bridge_script_path():
    return BASE_DIR / "xinput_to_keyboard.py"


def _controller_bridge_exe_path():
    return BASE_DIR / "XInputToKeyboard.exe"


def _controller_bridge_command():
    """The actual command to launch the Controller Bridge with - NOT
    just [sys.executable, script] unconditionally, because that
    silently does the wrong thing in a compiled build: sys.executable
    there is Meridian Launcher's OWN compiled exe, not a real Python
    interpreter, since a typical PyInstaller build doesn't bundle a
    standalone python.exe at all. Running "MeridianLauncher.exe
    xinput_to_keyboard.py" doesn't execute that script as Python - it
    just relaunches the compiled app with a file path as an ignored
    argument, which would make this feature silently do nothing in any
    real compiled install (the normal way this whole suite is actually
    distributed).

    Prefers a separately-compiled XInputToKeyboard.exe (see
    xinput_to_keyboard.spec - same idea as onscreenmenu.exe/
    CyberDeckBrowser.exe already being their own standalone compiled
    exes) if one exists next to this app. Only falls back to
    [sys.executable, xinput_to_keyboard.py] when NOT frozen (i.e.
    running from source with a real python.exe)."""
    exe = _controller_bridge_exe_path()
    if exe.exists():
        return [str(exe)]
    if not getattr(sys, "frozen", False):
        script = _controller_bridge_script_path()
        if script.exists():
            return [sys.executable, str(script)]
    return None


def _start_controller_bridge_for_path(path):
    """Starts the Controller Bridge in the background, then waits for
    the launched exe to actually appear (can take a few seconds -
    launchers/anti-cheat/etc) and then disappear (it closing) before
    killing the bridge. Runs entirely on a background thread so this
    never blocks the launch itself.

    Deliberately per-item (see toggle_controller_bridge_for_item), not a
    global toggle: this translates real controller input into keyboard
    presses system-wide while running, which would make the controller
    useless for navigating Meridian Launcher itself (different keyboard
    shortcuts) - or worse, get stuck fighting onscreenmenu/
    CyberDeckBrowser/Meridian Explorer's own, different keyboard
    shortcuts if any of those end up focused while it's running - if
    left on outside of the one app that actually needs it. Starting it
    right before that specific app launches and killing it the instant
    that specific app's process exits is what keeps it safe to use at
    all.

    Whether this can actually deliver keystrokes to an externally
    launched app: yes - the `keyboard` library's press()/release() on
    Windows go through SendInput/keybd_event, the same low-level global
    input injection every real keyboard-remapping tool (AutoHotkey,
    JoyToKey, AntiMicroX) uses. That's delivered to whatever window
    currently has OS keyboard focus, not a specific targeted process -
    which is exactly the launched app, as long as it's actually the
    focused window while it's being played/used, same expectation any
    of those other tools carry too."""
    cmd = _controller_bridge_command()
    if cmd is None:
        return
    exe_name = os.path.basename(path)

    def _watch():
        args = list(cmd)
        # Priority: an explicit global mapping file (chosen in Settings)
        # always wins if set; otherwise check the app/game's own install
        # folder for meridian_controller_bridge.json automatically (see
        # xinput_to_keyboard.py's --game-dir) - no per-item file browsing
        # needed for that common case.
        mapping_path = SETTINGS.get("controller_bridge_mapping_path")
        if mapping_path and os.path.isfile(mapping_path):
            args += ["--config", mapping_path]
        else:
            args += ["--game-dir", os.path.dirname(path)]
        try:
            proc = subprocess.Popen(
                args, cwd=str(BASE_DIR),
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
        except Exception:
            return
        try:
            # Wait for the app to actually start (up to 60s), then wait
            # for it to close, then clean up. If it never starts at all
            # within that window, don't leave the bridge running forever
            # for nothing.
            deadline = time.time() + 60
            appeared = False
            while time.time() < deadline:
                if system_actions.is_process_running(exe_name):
                    appeared = True
                    break
                time.sleep(1)
            if appeared:
                while system_actions.is_process_running(exe_name):
                    time.sleep(2)
        finally:
            try:
                proc.terminate()
            except Exception:
                pass

    threading.Thread(target=_watch, daemon=True).start()


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

    def list_installed_store_apps(self):
        """Populates the "Add Windows Store App" picker (Apps/Streaming
        sections) - see system_actions.list_installed_store_apps for how
        these are found and filtered down to genuine packaged apps."""
        return system_actions.list_installed_store_apps()

    def add_store_app_to_section(self, section_id, app_id, name):
        """Adds a Windows Store app (picked from list_installed_store_apps)
        to a section's item list - same shape as add_exe_to_section, just
        with a caller-supplied app_id/name instead of a file dialog, since
        there's no real file to pick from disk."""
        sec = _section_store(section_id)
        if sec is None:
            return []
        path = system_actions.STORE_APP_PATH_PREFIX + app_id
        if not any(it["path"] == path for it in sec["items"]):
            sec["items"].append({"path": path, "name": name or app_id})
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
        # Windows Store (UWP/MSIX) app item - not a real filesystem path,
        # so this has to be caught before any of the path-based logic
        # below (folder check, fullscreen helper, etc.) ever touches it.
        if path and path.startswith(system_actions.STORE_APP_PATH_PREFIX):
            ok, err = system_actions.launch_store_app(path)
            if ok and section_id and _section_launches_with_osm(section_id):
                _maybe_launch_osm()
            return {"ok": ok, "error": err}
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
            if (section_id in ("apps", "games")
                    and path in set(SETTINGS.get("controller_bridge_items", []))):
                _start_controller_bridge_for_path(path)
        return {"ok": ok, "error": err}

    def get_controller_bridge_enabled(self, path):
        return path in set(SETTINGS.get("controller_bridge_items", []))

    def toggle_controller_bridge_for_item(self, path):
        enabled = set(SETTINGS.get("controller_bridge_items", []))
        if path in enabled:
            enabled.discard(path)
        else:
            enabled.add(path)
        SETTINGS["controller_bridge_items"] = sorted(enabled)
        store.save_settings(SETTINGS)
        return SETTINGS

    def get_controller_bridge_mapping_path(self):
        return SETTINGS.get("controller_bridge_mapping_path")

    def set_controller_bridge_mapping_path(self):
        """Opens a file picker for a custom xinput_to_keyboard.py JSON
        mapping file, applied to every item the Controller Bridge is
        enabled for."""
        try:
            paths = webview.windows[0].create_file_dialog(
                _DLG_OPEN, file_types=("JSON files (*.json)", "All files (*.*)")
            )
        except Exception:
            paths = None
        if paths:
            SETTINGS["controller_bridge_mapping_path"] = paths[0]
            store.save_settings(SETTINGS)
        return SETTINGS.get("controller_bridge_mapping_path")

    def clear_controller_bridge_mapping_path(self):
        SETTINGS["controller_bridge_mapping_path"] = None
        store.save_settings(SETTINGS)
        return None

    def set_subfolder_filler_gif(self):
        """CyberRadial theme: opens a file picker for a custom gif/image
        shown in the subfolder bar for sections that don't have real
        subfolder content of their own (see setSubfolderNavHidden() in
        app.js). Returns the new SETTINGS dict."""
        try:
            paths = webview.windows[0].create_file_dialog(
                _DLG_OPEN, file_types=("Images (*.gif;*.png;*.jpg;*.jpeg;*.webp)", "All files (*.*)")
            )
        except Exception:
            paths = None
        if paths:
            SETTINGS["subfolder_filler_gif"] = "file:///" + paths[0].replace("\\", "/")
            store.save_settings(SETTINGS)
        return SETTINGS

    def clear_subfolder_filler_gif(self):
        SETTINGS["subfolder_filler_gif"] = None
        store.save_settings(SETTINGS)
        return SETTINGS

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

    def delete_desktop_item(self, path):
        """Sends a real Desktop file/folder to the Recycle Bin (not a
        permanent delete) - the Start menu's Delete option, only ever
        offered for actual Desktop-section items. Confirmation already
        happened on the frontend before this is called."""
        desktop_dir = os.path.normcase(os.path.abspath(
            str(Path(os.environ.get("USERPROFILE", str(Path.home()))) / "Desktop")
        ))
        target = os.path.normcase(os.path.abspath(path))
        if not target.startswith(desktop_dir):
            return {"ok": False, "error": "Refusing to delete something outside the Desktop folder."}
        ok, err = system_actions.delete_to_recycle_bin(path)
        return {"ok": ok, "error": err}

    def delete_media_item(self, kind, path):
        """Sends a real Photos/Videos/Music file to the Recycle Bin -
        the Start menu's Delete option there. Restricted to files inside
        one of that section's own configured library folders (SETTINGS
        ["folders"][kind]), same safety reasoning as delete_desktop_item:
        confirmation already happened on the frontend before this runs."""
        folders = SETTINGS.get("folders", {}).get(kind, [])
        target = os.path.normcase(os.path.abspath(path))
        if not any(target.startswith(os.path.normcase(os.path.abspath(f))) for f in folders if f):
            return {"ok": False, "error": "Refusing to delete something outside this section's configured folders."}
        ok, err = system_actions.delete_to_recycle_bin(path)
        return {"ok": ok, "error": err}

    def open_containing_folder(self, path):
        """Start menu's Open Folder option (Photos/Videos/Music) - opens
        Windows Explorer with the file itself highlighted/selected
        (explorer.exe's /select, convention), not just the bare folder
        with nothing selected."""
        if not path or not os.path.exists(path):
            return {"ok": False, "error": "That file no longer exists."}
        try:
            subprocess.Popen(f'explorer /select,"{os.path.normpath(path)}"')
            return {"ok": True, "error": None}
        except Exception as e:
            return {"ok": False, "error": str(e)}

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
        _ensure_plugon_server_started(plugin_id)
        url = plugin_manager.get_plugin_url(plugin_id)
        exe_field = "" if url else plugin_manager.get_plugin_exe_field(plugin_id)
        exe_path = None if url else plugin_manager.get_plugin_exe_path(plugin_id)
        if not url and not exe_field:
            return {"ok": False, "error": "This plugin has no url or exe configured in its plugin.json."}
        if exe_field and not exe_path:
            # The manifest DOES name an exe - it just isn't sitting next
            # to MeridianLauncher.exe yet, almost always because it
            # hasn't been built (see e.g. InternalLauncher.spec/
            # MeridianPaint.spec) rather than a plugin.json authoring
            # mistake - worth a message that actually says that instead
            # of the generic "not configured" one above.
            return {"ok": False, "error": f"{exe_field} isn't built/staged yet - see the plug-on's own README/spec for how to build it."}
        exe = exe_path if exe_path else BASE_DIR / "CyberDeckBrowser.exe"
        if not exe.exists():
            return {"ok": False, "error": f"{exe.name} not found."}
        self.unload_plugin_webapp_box(plugin_id)
        _close_onscreenmenu_if_running()
        try:
            if exe_path:
                # A real standalone program (e.g. Internal Launcher) -
                # boxed directly, no CyberDeckBrowser/--minimal-menu/url
                # involved at all.
                args = [str(exe), f"--box={int(x)},{int(y)},{int(w)},{int(h)}",
                        f"--notify-exit={plugin_id}"]
            else:
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
        """Close the boxed process for this plugin, if any, so it
        doesn't keep running in the background once the user leaves that
        section, and hand Meridian Launcher's own controls back.

        Closes gracefully (WM_CLOSE, via taskkill without /F) rather than
        an abrupt kill - this runs every single time someone leaves a
        plugin webapp section, so an abrupt TerminateProcess kill here
        meant Chromium's cookie/session database (and CyberDeckBrowser's
        own tab-session save in its closeEvent) never got a chance to
        flush to disk, which was very likely why plugin webapps' logins
        and sessions weren't actually persisting between restarts despite
        the profile itself being configured correctly - the process was
        being killed too abruptly to ever write anything down. Only
        force-kills as a fallback if the graceful close doesn't finish
        within a couple seconds (e.g. a truly hung renderer)."""
        global _plugin_webapp_procs
        proc = _plugin_webapp_procs.pop(plugin_id, None)
        if proc is not None:
            try:
                if proc.poll() is None:
                    try:
                        subprocess.run(
                            ["taskkill", "/PID", str(proc.pid)],
                            capture_output=True, timeout=5,
                            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                        )
                        proc.wait(timeout=3)
                    except Exception:
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
        "webapp" plugins appear after the last custom section; "option"/
        "addon" plugins don't get their own section at all — see
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
            if info.get("type") in ("option", "addon"):
                item["section"] = info.get("section", "chat")
            out.append(item)
        return out

    def list_section_options(self, section_id):
        """[{"id","label","pluginId","addon"?,"layout"?}] — the enabled
        "option"- and "addon"-type plugins targeting this section id
        (e.g. "chat", or any built-in section for an addon), in discovery
        order. Used to build a section (like Chat) whose entries are
        individually toggleable plugins rather than a fixed list, and to
        splice plug-on ("addon") entries into a built-in section's own
        list (see frontend/app.js's use of this for every built-in
        section, not just Chat).

        An addon is silently excluded here (regardless of its own
        "visible" setting) whenever its target section is itself hidden -
        there'd be nowhere for it to appear, and leaving it toggled on in
        that state would just make it pop back in, confusingly, the
        moment the section was unhidden again with no other change."""
        discovered = plugin_manager.scan_plugins()
        out = []
        for info in discovered:
            ptype = info.get("type")
            if ptype not in ("option", "addon") or info.get("section", "chat") != section_id:
                continue
            pid = info["id"]
            entry = SETTINGS.get("plugins", {}).get(pid, {"visible": False})
            if not entry.get("visible", False):
                continue
            if ptype == "addon" and not _is_builtin_section_visible(section_id):
                continue
            item = {"id": pid, "label": info["label"]}
            if ptype == "addon":
                item["addon"] = True
                item["layout"] = info.get("layout", dict(plugin_manager.ADDON_LAYOUT_DEFAULTS))
            out.append(item)
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

    def delete_plugin_item(self, plugin_id, item_id):
        return plugin_manager.delete_item(plugin_id, item_id)

    # ---------------- addon settings (plugins/plug-ons/drop-in themes) ----------------
    def list_addon_setting_groups(self):
        """Each group's fields come back with the CURRENT value merged in
        (as field["value"]) alongside its schema, so the frontend doesn't
        need a second round-trip per field to render correctly."""
        groups = addon_settings.scan_groups(BASE_DIR)
        for group in groups:
            values = addon_settings.get_all_values(SETTINGS, group["id"])
            for field in group["fields"]:
                field["value"] = values.get(field["key"], field.get("default"))
        return groups

    def set_addon_setting_value(self, namespace_id, key, value):
        addon_settings.set_value(SETTINGS, namespace_id, key, value)
        store.save_settings(SETTINGS)
        return SETTINGS

    def pick_addon_setting_file(self, namespace_id, key, accept):
        """Native file picker for a "file"-type addon setting field."""
        try:
            file_types = (accept, "All files (*.*)") if accept else ("All files (*.*)",)
            paths = webview.windows[0].create_file_dialog(_DLG_OPEN, file_types=file_types)
        except Exception:
            paths = None
        if paths:
            addon_settings.set_value(SETTINGS, namespace_id, key, paths[0])
            store.save_settings(SETTINGS)
        return SETTINGS

    # ---------------- macros ----------------
    def list_macro_items(self):
        builtin = [
            {"type": "builtin", "id": "close_others", "name": "Close all other programs"},
        ]
        # Internalized (see _toggle_default_shell) - no MakeUnmakeShell.ps1
        # file dependency anymore, so this is always offered rather than
        # gated on that file existing.
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
            whitelist.add("meridianlauncher.exe")
            whitelist.add(Path(sys.executable).name)
            return system_actions.close_all_except(whitelist)
        if macro_id == "toggle_default_shell":
            ok, error, message = _toggle_default_shell()
            return {"ok": ok, "error": error, "message": message}
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
        # Internalized - see _launch_onscreenmenu(), no osm.bat involved.
        _maybe_launch_osm()

    def system_shutdown(self):
        ok, err = system_actions.shutdown()
        return {"ok": ok, "error": err}

    def system_restart(self):
        ok, err = system_actions.restart()
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
        """Only ever one Explorer-family window at a time, across BOTH the
        standalone Meridian Explorer.exe and Meridian FileBrowse.exe (a
        separate compiled exe left over from the now-removed boxed/
        internal mode - checked here too in case one happens to still be
        running) - if either is already running, focus it instead of
        launching a second one."""
        if system_actions.focus_process_window("Meridian Explorer.exe"):
            return {"ok": True, "error": None}
        if system_actions.focus_process_window("Meridian FileBrowse.exe"):
            return {"ok": True, "error": None}
        exe = BASE_DIR / "Meridian Explorer.exe"
        if not exe.exists():
            return {"ok": False, "error": "Meridian_Explorer.exe not found in the app folder."}
        ok, err = system_actions.launch_path(str(exe))
        return {"ok": ok, "error": err}

    def open_desktop_entry(self, path, is_dir):
        """Called when the user activates a Desktop-section entry. Files
        keep going through the normal launch path; folders always open in
        standalone Meridian Explorer (external-only, no boxed/embedded
        mode anymore), falling back to Windows Explorer if it's missing."""
        if not is_dir:
            ok, err = system_actions.launch_path(path)
            return {"ok": ok, "error": err, "route": "launched"}

        exe = BASE_DIR / "Meridian Explorer.exe"
        if exe.exists():
            # Single instance: focus the existing window instead of
            # opening a second one - though a focused existing window
            # can't be handed this specific new path, so it's still
            # opened fresh only when nothing's running.
            if system_actions.focus_process_window("Meridian Explorer.exe"):
                return {"ok": True, "error": None, "route": "meridian_explorer"}
            ok, err = system_actions.launch_path(str(exe), args=[path])
            return {"ok": ok, "error": err, "route": "meridian_explorer"}
        ok, err = system_actions.open_folder(path)
        return {"ok": ok, "error": err, "route": "windows_explorer"}

    def open_meridian_explorer_path(self, path):
        """Target of the "Make Meridian Explorer the default shell
        browser" registration (see explorer_shell.py) - opens a path in
        standalone Meridian Explorer, external-only, same single-instance
        rule as open_desktop_entry/launch_meridian_explorer."""
        exe = BASE_DIR / "Meridian Explorer.exe"
        if not exe.exists():
            return {"ok": False, "error": "Meridian Explorer.exe not found in the app folder."}
        if system_actions.focus_process_window("Meridian Explorer.exe"):
            return {"ok": True, "error": None}
        ok, err = system_actions.launch_path(str(exe), args=[path] if path else None)
        return {"ok": ok, "error": err}

    # ---------------- Web section ----------------
    def open_picture_in_paint(self, path):
        """Pictures/Downloads sections' Start menu > "Open in Meridian
        Paint" option. Standalone (not boxed) - editing a picture is a
        deliberate side-trip, not something that belongs pinned inside
        whichever section you launched it from."""
        if not path or not os.path.isfile(path):
            return {"ok": False, "error": "That file no longer exists."}
        exe = BASE_DIR / "MeridianPaint.exe"
        if not exe.exists():
            return {"ok": False, "error": "MeridianPaint.exe isn't built/staged yet - see MeridianPaint/MeridianPaint.spec."}
        try:
            subprocess.Popen(
                [str(exe), path], cwd=str(BASE_DIR),
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            return {"ok": True, "error": None}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def launch_cyberdeckbrowser_standalone(self):
        """The Web section's own "CyberDeckBrowser" entry - this
        represents the PROGRAM itself, not a URL, so it always opens the
        real standalone app directly (the same way an Apps/Games item
        would) rather than going through open_web_link()'s Browser-
        section-routing / default-browser-fallback chain, which exists
        for actual URLs (Web-section shortcuts) and previously also
        (incorrectly) handled this entry, sometimes routing it into the
        boxed Browser section or the system default browser instead of
        opening CyberDeckBrowser itself."""
        cdb = BASE_DIR / "CyberDeckBrowser.exe"
        if not cdb.exists():
            return {"ok": False, "error": "CyberDeckBrowser.exe not found in the app folder."}
        _close_onscreenmenu_if_running()
        ok, err = system_actions.launch_path(str(cdb), args=[WINDOW_MODE_REQUEST_FLAG])
        return {"ok": ok, "error": err}

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
            _close_onscreenmenu_if_running()
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
        _close_onscreenmenu_if_running()
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
        """Close the boxed CyberDeckBrowser process, if any, so it
        doesn't keep running in the background once the user leaves the
        Browser section, and hand Meridian Launcher's own controls back.
        Graceful close (see unload_plugin_webapp_box's docstring for why -
        same fix, same reason: an abrupt kill here was very likely why
        the Browser section's own logins/sessions weren't persisting
        either)."""
        global _browser_box_proc
        if _browser_box_proc is not None:
            try:
                if _browser_box_proc.poll() is None:
                    try:
                        subprocess.run(
                            ["taskkill", "/PID", str(_browser_box_proc.pid)],
                            capture_output=True, timeout=5,
                            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                        )
                        _browser_box_proc.wait(timeout=3)
                    except Exception:
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
        _close_onscreenmenu_if_running()
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
        launch it directly (see _launch_onscreenmenu - no osm.bat
        involved) - never both (no double-launching)."""
        try:
            if system_actions.is_process_running("onscreenmenu.exe"):
                ok, err = system_actions.kill_process("onscreenmenu.exe")
                return {"ok": ok, "error": err}
            ok, err = _launch_onscreenmenu()
            return {"ok": ok, "error": err}
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

    def set_music_sort_mode(self, mode):
        if mode not in ("title_asc", "title_desc", "artist_asc", "artist_desc", "date_desc", "random"):
            mode = "title_asc"
        SETTINGS["music_sort_mode"] = mode
        store.save_settings(SETTINGS)
        return SETTINGS

    def set_play_random_song_on_startup(self, enabled):
        SETTINGS["play_random_song_on_startup"] = bool(enabled)
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
        if backend not in ("xinput", "gameinput", "directinput", "sdl3", "joycon_pair", "browser_gamepad", "auto"):
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
            "input_backend": SETTINGS.get("input_backend", "auto"),
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

    def dump_controller_diag_now(self):
        """Settings > Controls' "Dump Diagnostics Now" button - writes
        gameinput_api's diagnostic dump immediately instead of waiting
        for the automatic one a few minutes after startup (see
        gameinput_api._schedule_diag_dump). Useful when you don't want
        to wait, or want a fresh dump after just having moved sticks/
        pressed buttons. Returns {"ok", "path", "error"}."""
        import gameinput_api
        listener = _CONTROLLER_LISTENER
        backend_name = None
        if listener is not None:
            backend_name = listener.status().get("backend")
        try:
            gameinput_api._write_diag_dump(backend_name or "unknown")
            return {"ok": True, "path": gameinput_api._diag_dump_path(), "error": None}
        except Exception as e:
            return {"ok": False, "path": None, "error": str(e)}

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
        shouldn't move the cursor or open menus until the app is focused.

        Also closes onscreenmenu.exe on the rising edge of becoming
        foreground: it's a controller overlay meant for use over other,
        external apps, and has nothing to do once you're back in Meridian
        Launcher itself — left running it would otherwise sit on top of
        the Launcher UI, still capturing controller input alongside it.

        And: unloads whatever's currently boxed (Meridian Explorer/
        CyberDeckBrowser/a plugin webapp) the moment focus genuinely
        leaves Meridian entirely - not just when THIS window stops being
        foreground, since a boxed section is a real, separate top-level
        process; giving it focus (completely normal, expected use of it)
        ALSO makes GetForegroundWindow() report something other than
        Launcher's own hwnd. The distinction that matters is "still
        somewhere in Meridian" (this window, or whichever child it
        currently has boxed) vs. "something else entirely took focus" -
        only the second one means the section actually left the
        foreground and should be torn down, which is what was leaving
        Meridian Explorer running invisibly and causing errors."""
        try:
            import ctypes
            hwnd = ctypes.windll.user32.GetForegroundWindow()
            our = ctypes.windll.user32.FindWindowW(None, APP_TITLE)
            now_foreground = bool(hwnd and our and hwnd == our)
        except Exception:
            return True  # non-Windows or failure: don't gate

        global _WAS_FOREGROUND
        if now_foreground and not _WAS_FOREGROUND:
            _close_onscreenmenu_if_running()
        elif not now_foreground:
            self._unload_boxes_if_truly_backgrounded(hwnd)
        _WAS_FOREGROUND = now_foreground
        return now_foreground

    def _unload_boxes_if_truly_backgrounded(self, foreground_hwnd):
        """See is_foreground()'s docstring - only unloads if the current
        foreground window belongs to neither this process nor whichever
        child process is currently boxed."""
        if not foreground_hwnd:
            return
        try:
            fg_pid = wintypes.DWORD(0)
            ctypes.windll.user32.GetWindowThreadProcessId(foreground_hwnd, ctypes.byref(fg_pid))
            fg_pid = fg_pid.value
        except Exception:
            return
        if fg_pid == os.getpid():
            return  # some other window of our own (a dialog, etc.) - still us
        boxed_pids = set()
        if _browser_box_proc is not None and _browser_box_proc.poll() is None:
            boxed_pids.add(_browser_box_proc.pid)
        for proc in _plugin_webapp_procs.values():
            if proc is not None and proc.poll() is None:
                boxed_pids.add(proc.pid)
        if fg_pid in boxed_pids:
            return  # focus is on the boxed child itself - normal, expected use
        # Focus is genuinely on something outside Meridian entirely.
        if _browser_box_proc is not None:
            self.unload_browser_box()
        for plugin_id in list(_plugin_webapp_procs.keys()):
            self.unload_plugin_webapp_box(plugin_id)

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

    # ---------------- backup & restore ----------------
    def export_backup(self):
        """Settings > Program > Backup & Restore > Export. Opens a save
        dialog, then bundles settings.json, the control maps, and the
        real Plugins/ + themes/ folders into one .zip. Returns
        {"ok": bool, "error": str|None, "path": str|None} (path is None
        if the dialog was cancelled - not an error)."""
        try:
            result = webview.windows[0].create_file_dialog(
                _DLG_SAVE,
                save_filename=f"MeridianLauncher-backup-{time.strftime('%Y-%m-%d')}.zip",
                file_types=("Zip files (*.zip)", "All files (*.*)"),
            )
        except Exception as e:
            return {"ok": False, "error": str(e), "path": None}
        dest = result[0] if isinstance(result, (list, tuple)) else result
        if not dest:
            return {"ok": True, "error": None, "path": None}
        outcome = backup_restore.export_backup(BASE_DIR, dest, CURRENT_VERSION)
        outcome["path"] = dest if outcome.get("ok") else None
        return outcome

    def pick_backup_to_import(self):
        """Opens a picker for a backup .zip and returns what's inside it
        (via inspect_backup) without applying anything yet, so the
        frontend can show a confirmation before import_backup() actually
        overwrites anything. Returns {"ok", "error", "path", "manifest",
        "has_plugins", "has_themes"} - path is None if cancelled."""
        try:
            paths = webview.windows[0].create_file_dialog(
                _DLG_OPEN, file_types=("Zip files (*.zip)", "All files (*.*)")
            )
        except Exception as e:
            return {"ok": False, "error": str(e), "path": None}
        if not paths:
            return {"ok": True, "error": None, "path": None}
        path = paths[0]
        info = backup_restore.inspect_backup(path)
        info["path"] = path
        return info

    def import_backup(self, zip_path):
        """Applies a backup previously chosen via pick_backup_to_import().
        Reloads SETTINGS in-place from the restored settings.json and
        re-scans Plugins/ so newly-restored plugin folders show up
        immediately, without requiring an app restart. Returns
        {"ok": bool, "error": str|None, "settings": dict|None}."""
        outcome = backup_restore.import_backup(BASE_DIR, zip_path)
        if not outcome.get("ok"):
            outcome["settings"] = None
            return outcome
        for pid in list(SETTINGS.get("plugins", {}).keys()):
            plugin_manager.unload_backend(pid)
        SETTINGS.clear()
        SETTINGS.update(store.load_settings())
        _rescan_plugins()
        outcome["settings"] = SETTINGS
        return outcome

    # ---------------- Audio Output ----------------
    def list_audio_devices(self):
        try:
            err = audio_devices.import_error()
            if err is not None:
                return {"ok": False, "devices": [], "error": "Audio Output unavailable: " + err}
            devices = audio_devices.list_output_devices()
            return {"ok": True, "devices": devices, "error": None}
        except Exception as e:
            return {"ok": False, "devices": [], "error": str(e)}

    def set_audio_output_device(self, device_id):
        return audio_devices.set_default_output_device(device_id)

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
        if ok:
            # launch_path only requests a maximized window, not foreground
            # focus - Windows' own foreground-lock behavior for a freshly
            # spawned process is unreliable enough in practice that Game
            # Library often stayed behind Meridian Launcher instead of
            # actually taking over. Poll for its window (it takes a moment
            # to actually appear) and explicitly focus it, then send
            # Meridian Launcher itself to the background once that's done.
            threading.Thread(target=_focus_game_library_and_background_self, daemon=True).start()
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

def _focus_game_library_and_background_self(timeout=10.0):
    """Polls for Meridian Game Library's window to actually exist (it
    takes a moment after the process starts), focuses it once found using
    the same AttachThreadInput technique as everything else here that
    fights Windows' foreground-lock behavior, then minimizes Meridian
    Launcher's own window so it's genuinely out of the way rather than
    just sitting behind Game Library still fully rendered."""
    deadline = time.time() + timeout
    focused = False
    while time.time() < deadline:
        if system_actions.focus_process_window("Meridian Game Library.exe"):
            focused = True
            break
        time.sleep(0.2)
    if not focused:
        return
    if win32gui is None:
        return
    try:
        hwnd = win32gui.FindWindow(None, APP_TITLE)
        if hwnd:
            win32gui.ShowWindow(hwnd, win32con.SW_MINIMIZE)
    except Exception:
        pass


def _bring_to_foreground():
    """Brings Meridian Launcher's window to the foreground - the Start+
    Select combo's whole job. Plain SetForegroundWindow often silently
    does nothing here: Windows' foreground-lock protection blocks a
    background process from stealing focus unless it currently "owns"
    it in some way (recently sent real input, is already foreground,
    etc) - and this call comes from the controller-polling background
    thread of a background/minimized app, precisely the case that
    protection exists to block. AttachThreadInput is the standard,
    long-documented workaround: briefly attach this thread's input
    state to the current foreground window's thread, which satisfies
    that check, make the call, then detach again immediately after."""
    if win32gui is None:
        return
    try:
        hwnd = win32gui.FindWindow(None, APP_TITLE)
        if not hwnd:
            return
        if win32gui.IsIconic(hwnd):
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)

        cur_thread = win32api.GetCurrentThreadId()
        fg_hwnd = win32gui.GetForegroundWindow()
        fg_thread = 0
        if fg_hwnd and win32process is not None:
            try:
                fg_thread, _ = win32process.GetWindowThreadProcessId(fg_hwnd)
            except Exception:
                fg_thread = 0

        attached = False
        if fg_thread and fg_thread != cur_thread:
            try:
                attached = bool(ctypes.windll.user32.AttachThreadInput(fg_thread, cur_thread, True))
            except Exception:
                attached = False

        try:
            win32gui.BringWindowToTop(hwnd)
            win32gui.SetForegroundWindow(hwnd)
        finally:
            if attached:
                try:
                    ctypes.windll.user32.AttachThreadInput(fg_thread, cur_thread, False)
                except Exception:
                    pass
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

# Set (via a background poll of a small shared flag file, not checked
# per-frame directly - see _watch_external_menu_flag below) whenever a
# standalone Meridian Explorer instance has a menu/popup open. XInput/
# DirectInput have no OS-level concept of "exclusive" access - nothing
# can literally stop an unrelated third-party program from also reading
# the same physical controller - but Meridian Launcher itself CAN (and
# should) get out of the way while Explorer's own menu wants sole
# control of it, the same way boxed Explorer/Browser sections already do.
_external_menu_open = False

_EXTERNAL_MENU_FLAG_FILE = None


def _external_menu_flag_path():
    global _EXTERNAL_MENU_FLAG_FILE
    if _EXTERNAL_MENU_FLAG_FILE is None:
        base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
        shared_dir = os.path.join(base, "Meridian Launcher", "shared")
        try:
            os.makedirs(shared_dir, exist_ok=True)
        except Exception:
            pass
        _EXTERNAL_MENU_FLAG_FILE = os.path.join(shared_dir, "external_menu_open.flag")
    return _EXTERNAL_MENU_FLAG_FILE


def _watch_external_menu_flag():
    """Background thread: checks every 200ms (fast enough to feel
    immediate, cheap enough not to matter) whether the shared flag file a
    standalone Meridian Explorer writes while a menu is open still
    exists, and updates _external_menu_open accordingly."""
    global _external_menu_open
    path = _external_menu_flag_path()
    while True:
        try:
            _external_menu_open = os.path.exists(path)
        except Exception:
            pass
        time.sleep(0.2)


def suspend_main_controls(suspended=True):
    global _controller_suspended_for_plugin
    _controller_suspended_for_plugin = bool(suspended)


def _controls_suspended():
    return _controller_suspended_for_plugin or _external_menu_open


def _watch_browser_box_exit(proc):
    """Same as the old boxed-Explorer watcher (now removed - Explorer is
    external-only), for the boxed Meridian NetBrowse process in the
    Browser section."""
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
    if _controls_suspended():
        return
    # record it for the settings debugger before dispatching
    _LAST_CONTROLLER_ACTION[0] = action_name
    _LAST_CONTROLLER_ACTION[1] = time.time()
    try:
        webview.windows[0].evaluate_js(f"window.handleControllerInput && window.handleControllerInput('{action_name}')")
    except Exception:
        pass


def _controller_any():
    if _controls_suspended():
        return
    try:
        webview.windows[0].evaluate_js("window.handleControllerAny && window.handleControllerAny()")
    except Exception:
        pass


def _controller_raw_button(name):
    """Forwards raw DPAD/A/B rising edges to the frontend, independent of
    whatever the user has confirm/back remapped to — used only to watch for
    the kiosk-mode secret unlock sequence."""
    if _controls_suspended():
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
            # Single-instance rule (see Api.launch_meridian_explorer's
            # docstring): focus an already-running Explorer-family window
            # rather than opening a second one. It can't be handed this
            # specific new path once already running/focused, same
            # trade-off as the Desktop-entry fallback makes.
            if (system_actions.focus_process_window("Meridian Explorer.exe")
                    or system_actions.focus_process_window("Meridian FileBrowse.exe")):
                return True, None
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
        input_backend=SETTINGS.get("input_backend", "auto"),
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
    threading.Thread(target=_watch_external_menu_flag, daemon=True).start()
    webview.start(
        _check_for_update_at_boot, window,
        debug=False, gui="edgechromium",
    )


if __name__ == "__main__":
    main()
