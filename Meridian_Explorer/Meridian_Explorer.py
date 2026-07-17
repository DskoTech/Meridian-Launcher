import os
import sys

from crash_logger import install_crash_logging
install_crash_logging("Meridian Explorer")

try:
    from meridian_editors import run_text_editor, run_hex_editor
except Exception:  # editors are optional; the browser must still run
    run_text_editor = run_hex_editor = None
import json
import time
import shutil
import string
import ctypes
import subprocess
import collections


def _app_base_dir():
    """Folder the Explorer runs from — next to onscreenmenu and the rest of
    the suite. Handles both frozen (PyInstaller exe) and source runs."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def launch_onscreenmenu():
    """Start the onscreenmenu controller overlay via osm.bat (not
    onscreenmenu.exe directly) if it's present next to us. Used when a
    native Windows dialog (e.g. the 'Open with' picker) is about to
    appear, so it can be driven with a controller. Best-effort: silently
    does nothing if osm.bat isn't found."""
    base = _app_base_dir()
    bat = os.path.join(base, "osm.bat")
    if os.path.isfile(bat):
        try:
            subprocess.Popen(["cmd.exe", "/c", bat], cwd=base)
            return True
        except Exception:
            pass
    # source fallback: run onscreenmenu's .py directly if present (osm.bat
    # itself is missing, e.g. running from source rather than an install)
    py = os.path.join(base, "onscreenmenu", "onscreenmenu.py")
    if os.path.isfile(py):
        try:
            subprocess.Popen([sys.executable, py], cwd=os.path.dirname(py))
            return True
        except Exception:
            pass
    return False


# Programs considered "part of the Meridian suite" — opening/those with these
# doesn't need the onscreenmenu overlay, since they're already controller-first.
_MERIDIAN_EXES = {
    "meridian explorer.exe", "meridianlauncher.exe", "meridian game library.exe",
    "cyberdeckbrowser.exe", "onscreenmenu.exe",
}


def _is_meridian_program(path):
    try:
        return os.path.basename(path).lower() in _MERIDIAN_EXES
    except Exception:
        return False


_IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".gif", ".webp", ".tiff", ".jfif"}


def _is_image_file(name):
    dot = name.rfind(".")
    return dot > 0 and name[dot:].lower() in _IMAGE_EXTS
# Prevent the fullscreen pygame window from auto-minimizing when it loses
# OS focus (e.g. when the Y-menu "Edit"/"Open" actions launch Notepad or
# another external app). Without this, the window drops to the background
# and stops receiving controller/keyboard input until manually restored.
os.environ.setdefault("SDL_VIDEO_MINIMIZE_ON_FOCUS_LOSS", "0")
# Keep SDL/pygame explicitly DPI-unaware. Meridian Launcher computes the
# --box=X,Y,W,H geometry for boxed mode from its own (Chromium/WebView2)
# logical/CSS pixel space — a DPI-AWARE pygame window would instead size
# and position itself in physical pixels, which disagree by exactly the
# Windows scaling factor (e.g. 2x at 200% on a 4K display) and would
# confine/misplace the window the same way an earlier bug confined
# CyberDeckBrowser's virtual cursor to a quarter of the screen. Explicit
# rather than relying on whatever a given PyInstaller build happens to
# default to.
os.environ.setdefault("SDL_WINDOWS_DPI_AWARENESS", "unaware")
import pygame
# GameInput backend (fixes Windows 11 Xbox fullscreen experience, where
# SDL/pygame joysticks can receive no input at all). SDLJoystickShim exposes
# the pygame.joystick.Joystick read API, so handle_controller() is unchanged.
try:
    from gameinput_api import open_gamepad, SDLJoystickShim
except ImportError:
    open_gamepad = None
    SDLJoystickShim = None
# --------------------------------------------------------------------------- #
# CONFIG
# --------------------------------------------------------------------------- #
COOLDOWN = 0.2 # seconds between accepted controller inputs
FAST_SCROLL_COOLDOWN = 0.05 # trigger-held repeat rate for fast scrolling
STICK_DEADZONE = 0.5
TRIGGER_DEADZONE = 0.1 # analog trigger axis: -1 released -> 1 fully pressed
SELECT_HOLD_TIME = 0.35 # how long Back/Select must be held to enter multi mode
DOUBLE_CLICK_TIME = 0.4
ROW_HEIGHT = 38
HEADER_HEIGHT = 90
FOOTER_HEIGHT = 60
PANE_GAP = 14
FONT_NAME = "consolas"
THISPC = "THISPC" # sentinel path meaning "show the drive-selection root"
STATE_FILE_LEGACY = os.path.join(os.path.expanduser("~"), ".meridian_explorer_state.json")
_local_appdata = os.environ.get("LOCALAPPDATA") or os.path.join(os.path.expanduser("~"), "AppData", "Local")
DATA_DIR = os.path.join(_local_appdata, "Meridian Launcher", "Meridian Explorer")
os.makedirs(DATA_DIR, exist_ok=True)
STATE_FILE = os.path.join(DATA_DIR, "state.json")
if os.path.exists(STATE_FILE_LEGACY) and not os.path.exists(STATE_FILE):
    try:
        shutil.copy2(STATE_FILE_LEGACY, STATE_FILE)
    except OSError:
        pass
# --- Color palettes: dark "console" (night) and a light (day) variant ----- #
# The COL_* names below are module globals read fresh every frame by the
# draw code, so apply_palette() can swap the whole scheme live (day/night).
_PALETTES = {
    "night": {
        "BG": (14, 16, 22), "PANE_BG": (22, 25, 34), "PANE_BORDER": (40, 44, 58),
        "ACTIVE_EDGE": (90, 200, 255), "TEXT": (225, 228, 235), "DIM_TEXT": (130, 136, 150),
        "FOLDER": (255, 205, 100), "FILE": (170, 200, 230), "DRIVE": (140, 230, 170),
        "SELECT_BG": (46, 100, 140), "SELECT_BG_INACTIVE": (34, 38, 50),
        "MULTI_MARK": (255, 150, 60), "HEADER_BG": (18, 20, 28), "FOOTER_BG": (18, 20, 28),
        "ACCENT": (90, 200, 255), "POPUP_BG": (26, 29, 40), "POPUP_BORDER": (90, 200, 255),
        "POPUP_ITEM_HL": (46, 100, 140), "DANGER": (230, 90, 90),
    },
    "day": {
        "BG": (238, 240, 245), "PANE_BG": (252, 253, 255), "PANE_BORDER": (200, 206, 218),
        "ACTIVE_EDGE": (40, 120, 200), "TEXT": (28, 32, 40), "DIM_TEXT": (110, 118, 132),
        "FOLDER": (210, 150, 40), "FILE": (70, 110, 160), "DRIVE": (40, 150, 90),
        "SELECT_BG": (180, 210, 240), "SELECT_BG_INACTIVE": (224, 228, 236),
        "MULTI_MARK": (230, 120, 30), "HEADER_BG": (228, 231, 238), "FOOTER_BG": (228, 231, 238),
        "ACCENT": (40, 120, 200), "POPUP_BG": (248, 249, 252), "POPUP_BORDER": (40, 120, 200),
        "POPUP_ITEM_HL": (180, 210, 240), "DANGER": (200, 60, 60),
    },
}


def apply_palette(mode):
    """Swap all COL_* globals to the given palette ('day' or 'night').
    Called at startup and whenever the View submenu changes the mode."""
    pal = _PALETTES.get(mode, _PALETTES["night"])
    g = globals()
    for key, val in pal.items():
        g["COL_" + key] = val


# Initialize with the dark theme; overridden at startup per saved/system mode.
COL_BG = COL_PANE_BG = COL_PANE_BORDER = COL_ACTIVE_EDGE = COL_TEXT = COL_DIM_TEXT = None
COL_FOLDER = COL_FILE = COL_DRIVE = COL_SELECT_BG = COL_SELECT_BG_INACTIVE = None
COL_MULTI_MARK = COL_HEADER_BG = COL_FOOTER_BG = COL_ACCENT = None
COL_POPUP_BG = COL_POPUP_BORDER = COL_POPUP_ITEM_HL = COL_DANGER = None
apply_palette("night")
Entry = collections.namedtuple("Entry", "name is_dir size is_drive")

# Current sort settings, kept in sync from MeridianExplorer.sync_sort() so
# Pane.refresh() (which has no app reference) can honor them.
SORT_STATE = {"key": "name", "desc": False}


def _entry_ext(name):
    dot = name.rfind(".")
    return name[dot + 1:].lower() if dot > 0 else ""


def _sort_entries(entries, base_path):
    key = SORT_STATE.get("key", "name")
    desc = SORT_STATE.get("desc", False)
    if key == "size":
        entries.sort(key=lambda e: (e.size if e.size is not None else -1, e.name.lower()))
    elif key == "type":
        entries.sort(key=lambda e: (_entry_ext(e.name), e.name.lower()))
    elif key == "modified":
        def mtime(e):
            try:
                return os.path.getmtime(os.path.join(base_path, e.name))
            except OSError:
                return 0
        entries.sort(key=mtime)
    else:  # name
        entries.sort(key=lambda e: e.name.lower())
    if desc:
        entries.reverse()

def human_size(num_bytes):
    if num_bytes is None:
        return ""
    step = 1024.0
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if num_bytes < step:
            return f"{num_bytes:3.0f}{unit}"
        num_bytes /= step
    return f"{num_bytes:.1f}PB"
def list_windows_drives():
    """Return a list of Entry objects for every mounted Windows drive letter."""
    drives = []
    if not sys.platform.startswith("win"):
        return [Entry("/", True, None, True)]
    bitmask = ctypes.windll.kernel32.GetLogicalDrives()
    for i, letter in enumerate(string.ascii_uppercase):
        if not (bitmask & (1 << i)):
            continue
        root = f"{letter}:\\"
        label_buf = ctypes.create_unicode_buffer(261)
        ctypes.windll.kernel32.GetVolumeInformationW(
            ctypes.c_wchar_p(root), label_buf, ctypes.sizeof(label_buf),
            None, None, None, None, 0
        )
        label = label_buf.value or "Local Disk"
        drives.append(Entry(f"{root}||{label}", True, None, True))
    return drives
def recycle_bin_delete(paths):
    """
    Send files/folders to the Recycle Bin (Windows) using the native
    shell API so nothing is permanently deleted. Falls back to a normal
    delete on non-Windows platforms (no recycle bin concept there).
    """
    if sys.platform.startswith("win"):
        class SHFILEOPSTRUCTW(ctypes.Structure):
            _fields_ = [
                ("hwnd", ctypes.c_void_p),
                ("wFunc", ctypes.c_uint),
                ("pFrom", ctypes.c_wchar_p),
                ("pTo", ctypes.c_wchar_p),
                ("fFlags", ctypes.c_uint16),
                ("fAnyOperationsAborted", ctypes.c_int),
                ("hNameMappings", ctypes.c_void_p),
                ("lpszProgressTitle", ctypes.c_wchar_p),
            ]
        FO_DELETE = 3
        FOF_ALLOWUNDO = 0x40 # send to recycle bin instead of deleting
        FOF_NOCONFIRMATION = 0x10
        FOF_SILENT = 0x4
        # pFrom must be a double-null-terminated string of paths
        joined = "\0".join(paths) + "\0\0"
        op = SHFILEOPSTRUCTW()
        op.wFunc = FO_DELETE
        op.pFrom = joined
        op.fFlags = FOF_ALLOWUNDO | FOF_NOCONFIRMATION | FOF_SILENT
        ctypes.windll.shell32.SHFileOperationW(ctypes.byref(op))
    else:
        for p in paths:
            try:
                if os.path.isdir(p) and not os.path.islink(p):
                    shutil.rmtree(p)
                else:
                    os.remove(p)
            except OSError:
                pass
class Pane:
    """A single directory-listing column (left or right)."""
    def __init__(self, path=None):
        self.path = path if path and (path == THISPC or os.path.isdir(path)) else THISPC
        self.entries = []
        self.selected = 0
        self.scroll = 0
        self.multi_selected = set() # indices currently multi-selected
        self.refresh()
    # ---- listing -------------------------------------------------------- #
    def refresh(self):
        self.multi_selected = set()
        if self.path == THISPC:
            self.entries = list_windows_drives()
            self.selected = min(self.selected, max(0, len(self.entries) - 1))
            self.scroll = 0
            return
        try:
            names = os.listdir(self.path)
        except (PermissionError, FileNotFoundError, NotADirectoryError):
            names = []
        dirs, files = [], []
        for name in names:
            full = os.path.join(self.path, name)
            if os.path.isdir(full):
                dirs.append(Entry(name, True, None, False))
            else:
                try:
                    size = os.path.getsize(full)
                except OSError:
                    size = None
                files.append(Entry(name, False, size, False))
        # Directories always group before files; within each group, sort by
        # the app's current sort key/direction (see SORT_STATE, kept in sync
        # by MeridianExplorer). Name is the default.
        _sort_entries(dirs, self.path)
        _sort_entries(files, self.path)
        self.entries = dirs + files
        self.selected = min(self.selected, max(0, len(self.entries) - 1))
        self.scroll = 0
    def current_entry(self):
        if 0 <= self.selected < len(self.entries):
            return self.entries[self.selected]
        return None
    def full_path_of(self, entry):
        if entry.is_drive:
            return entry.name.split("||")[0]
        return os.path.join(self.path, entry.name)
    def display_name_of(self, entry):
        if entry.is_drive:
            # Drive entries encode "C:\||Volume Label"; tolerate a missing
            # label rather than raising.
            parts = entry.name.split("||")
            if len(parts) >= 2:
                return f"{parts[0]} ({parts[1]})"
            return parts[0]
        return entry.name
    # ---- navigation ------------------------------------------------------ #
    def move(self, delta):
        if not self.entries:
            return
        self.selected = max(0, min(len(self.entries) - 1, self.selected + delta))
    def enter(self):
        entry = self.current_entry()
        if entry is None:
            return
        if entry.is_drive:
            self.path = entry.name.split("||")[0]
            self.refresh()
        elif entry.is_dir:
            self.path = self.full_path_of(entry)
            self.refresh()
        else:
            self._launch_file(self.full_path_of(entry))
    def go_up(self):
        """Go to parent directory, or back to This PC from a drive root."""
        if self.path == THISPC:
            return
        parent = os.path.dirname(self.path.rstrip(os.sep))
        if not parent or parent == self.path or parent == "":
            # We were sitting at a drive root (e.g. "C:\\") -> go to This PC
            old = self.path
            self.path = THISPC
            self.refresh()
            for i, e in enumerate(self.entries):
                if e.is_drive and e.name.split("||")[0].lower() == old.lower():
                    self.selected = i
                    break
        else:
            old = self.path
            self.path = parent
            self.refresh()
            base = os.path.basename(old)
            for i, e in enumerate(self.entries):
                if e.name == base:
                    self.selected = i
                    break
    def reveal_in_explorer(self):
        target = self.path if self.path != THISPC else None
        if not target:
            return
        try:
            if sys.platform.startswith("win"):
                os.startfile(target) # noqa
            elif sys.platform == "darwin":
                subprocess.Popen(["open", target])
            else:
                subprocess.Popen(["xdg-open", target])
        except Exception:
            pass
    @staticmethod
    def _launch_file(full_path):
        try:
            if sys.platform.startswith("win"):
                os.startfile(full_path) # noqa
            elif sys.platform == "darwin":
                subprocess.Popen(["open", full_path])
            else:
                subprocess.Popen(["xdg-open", full_path])
            launch_onscreenmenu()
        except Exception:
            pass
    # ---- multi-select helpers --------------------------------------- #
    def toggle_current_multi(self):
        if not self.entries:
            return
        if self.selected in self.multi_selected:
            self.multi_selected.discard(self.selected)
        else:
            self.multi_selected.add(self.selected)
    def select_all(self):
        self.multi_selected = set(range(len(self.entries)))
    def clear_multi(self):
        self.multi_selected = set()
    def multi_target_paths(self):
        """Return full paths for the current multi-selection (or the
        highlighted entry if nothing is explicitly multi-selected)."""
        indices = self.multi_selected if self.multi_selected else (
            {self.selected} if self.current_entry() else set()
        )
        paths = []
        for i in indices:
            if 0 <= i < len(self.entries):
                e = self.entries[i]
                if not e.is_drive:
                    paths.append(self.full_path_of(e))
        return paths
class Cooldown:
    """Simple per-key rate limiter so held buttons/sticks don't spam actions."""
    def __init__(self, delay=COOLDOWN):
        self.delay = delay
        self._last = {}
    def ready(self, key, delay=None):
        now = time.time()
        last = self._last.get(key, 0)
        if now - last >= (delay if delay is not None else self.delay):
            self._last[key] = now
            return True
        return False
class MeridianExplorer:
    def __init__(self, start_path=None, box=None):
        pygame.init()
        pygame.display.set_caption("Meridian Explorer")
        if box:
            # "Boxed" mode: used when Meridian Launcher's Explorer section is
            # visible but hasn't loaded the full in-process Meridian
            # FileBrowse plugin — this standalone copy of Meridian Explorer
            # is launched sized/positioned to sit exactly inside the
            # Launcher's list-frame box instead of covering the screen.
            x, y, w, h = box
            self.width, self.height = max(200, w), max(150, h)
            os.environ["SDL_VIDEO_WINDOW_POS"] = f"{x},{y}"
        else:
            info = pygame.display.Info()
            self.width, self.height = info.current_w, info.current_h
            # Borderless windowed fullscreen (a frameless window sized/
            # positioned to exactly cover the screen) instead of an OS-exclusive
            # display-mode fullscreen switch.
            os.environ["SDL_VIDEO_WINDOW_POS"] = "0,0"
        self.screen = pygame.display.set_mode((self.width, self.height), pygame.NOFRAME)
        self.clock = pygame.time.Clock()
        self.cooldown = Cooldown(COOLDOWN)
        self.font_header = pygame.font.SysFont(FONT_NAME, 26, bold=True)
        self.font_row = pygame.font.SysFont(FONT_NAME, 19)
        self.font_footer = pygame.font.SysFont(FONT_NAME, 17)
        self.font_title = pygame.font.SysFont(FONT_NAME, 30, bold=True)
        self.font_popup = pygame.font.SysFont(FONT_NAME, 22)
        left_path, right_path = self.load_state()
        if start_path:
            # Launched with a folder to show (command line / shell handler):
            # it takes over the left pane and gets focus; the right pane
            # still resumes wherever it last was.
            left_path = start_path
        self.panes = [Pane(left_path), Pane(right_path)]
        self.active_pane = 0
        self.single_pane = self._load_single_pane()  # remembered across runs
        # View mode: how entries are laid out. "text" (name list, current
        # look), "list" (small icon + name list), "icon" (medium icons in a
        # grid), "gallery" (large icons in a grid). Mirrors the Launcher's
        # list/gallery styles, minus theming.
        prefs = self._load_prefs()
        self.view_mode = prefs.get("view_mode", "text")
        # Sort: key + direction. key in name|size|type|modified.
        self.sort_key = prefs.get("sort_key", "name")
        self.sort_desc = bool(prefs.get("sort_desc", False))
        # Day/night theme: "system" follows the OS, else "day"/"night".
        self.theme_mode = prefs.get("theme_mode", "system")
        apply_palette(self._effective_theme())
        # Three-pane "quick access" mode (Windows-Explorer-like left rail).
        self.three_pane = bool(prefs.get("three_pane", False))
        self.quick_access = prefs.get("quick_access", [])  # user custom shortcuts
        self.quick_selected = 0
        # Undo/redo stacks for move operations.
        self.undo_stack = []
        self.redo_stack = []
        # Clipboard for copy/cut -> paste
        self.clipboard = {"op": None, "paths": []} # op: "copy" | "cut"
        # Multi-select / select-all state
        self.multi_active = False
        self.multi_pane_index = None
        self._select_hold_start = None
        # Popup / modal state machine:
        # "browse" | "menu" | "confirm_delete" | "confirm_selectall" | "text_input"
        self.state = "browse"
        self.menu_options = []
        self.menu_selected = 0
        self.menu_pane_index = 0
        self.menu_is_multi = False
        self.pending_delete_paths = []
        self.text_input_mode = None # "rename" | "extension"
        self.text_input_value = ""
        self.text_input_queue = [] # remaining full paths to process
        self.text_input_current = None
        self.flash_message = ""
        self.flash_until = 0
        self._last_click_time = 0
        self._last_click_pos = None
        # Controller: gameinput_api.open_gamepad() already tries XInput
        # (the default - plain, stable, fully-public API, correctly
        # reports every button/trigger/stick) then GameInput, DirectInput,
        # and SDL3 in one unified call with proper plausibility checks -
        # no need to hand-roll a separate fallback chain here (this used
        # to prefer GameInput first, which had known reliability issues
        # with sticks/triggers on real hardware).
        self.joysticks = []
        if open_gamepad is not None:
            pad = open_gamepad()
            if pad is not None:
                self.joysticks = [SDLJoystickShim(pad)]
        if not self.joysticks:
            # Last resort: raw pygame/SDL2 joystick, if gameinput_api
            # itself couldn't find anything usable.
            pygame.joystick.init()
            self.joysticks = [pygame.joystick.Joystick(i) for i in range(pygame.joystick.get_count())]
            for j in self.joysticks:
                j.init()
        self.running = True
        # Apply the saved sort to the initial pane listings.
        self.sync_sort()
    # ------------------------------------------------------------------ #
    # STATE PERSISTENCE
    # ------------------------------------------------------------------ #
    def load_state(self):
        """First run ever -> both panes start at This PC. Otherwise resume
        each pane's last folder (falling back to This PC if it's gone)."""
        if not os.path.exists(STATE_FILE):
            return THISPC, THISPC
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            left = data.get("left", THISPC)
            right = data.get("right", THISPC)
            if left != THISPC and not os.path.isdir(left):
                left = THISPC
            if right != THISPC and not os.path.isdir(right):
                right = THISPC
            return left, right
        except (json.JSONDecodeError, OSError):
            return THISPC, THISPC
    def _load_single_pane(self):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return bool(json.load(f).get("single_pane", False))
        except (json.JSONDecodeError, OSError):
            return False

    def _load_prefs(self):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f) or {}
        except (json.JSONDecodeError, OSError):
            return {}

    def _system_is_light(self):
        """True if Windows is in light mode (AppsUseLightTheme=1). Defaults
        to dark elsewhere / on any failure."""
        if not sys.platform.startswith("win"):
            return False
        try:
            import winreg
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize")
            try:
                val, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
                return bool(val)
            finally:
                winreg.CloseKey(key)
        except Exception:
            return False

    def _effective_theme(self):
        if self.theme_mode == "day":
            return "day"
        if self.theme_mode == "night":
            return "night"
        return "day" if self._system_is_light() else "night"  # system

    def sync_sort(self):
        """Push the app's sort settings into the module SORT_STATE so panes
        pick them up, then refresh both panes."""
        SORT_STATE["key"] = self.sort_key
        SORT_STATE["desc"] = self.sort_desc
        for p in self.panes:
            p.refresh()

    def save_state(self):
        try:
            with open(STATE_FILE, "w", encoding="utf-8") as f:
                json.dump({
                    "left": self.panes[0].path,
                    "right": self.panes[1].path,
                    "single_pane": self.single_pane,
                    "view_mode": self.view_mode,
                    "sort_key": self.sort_key,
                    "sort_desc": self.sort_desc,
                    "theme_mode": self.theme_mode,
                    "three_pane": self.three_pane,
                    "quick_access": self.quick_access,
                }, f)
        except OSError:
            pass
    # ------------------------------------------------------------------ #
    # CUSTOM ACTION HOOK
    # ------------------------------------------------------------------ #
    def select_option(self):
        """
        Placeholder hook for future custom behavior after any action is
        confirmed (sound effect, logging, plugin call, etc). Currently a
        no-op; wire up custom logic here as needed.
        """
        pass
    def switch_pane(self, direction):
        if self.multi_active:
            return # pane switching is locked while multi-select is active
        self.active_pane = (self.active_pane + direction) % len(self.panes)
    # ------------------------------------------------------------------ #
    # FILE OPERATIONS
    # ------------------------------------------------------------------ #
    def other_pane(self, index):
        return self.panes[1 - index]
    def do_copy(self, paths):
        self.clipboard = {"op": "copy", "paths": list(paths)}
    def do_cut(self, paths):
        self.clipboard = {"op": "cut", "paths": list(paths)}
    def do_paste(self, dest_dir):
        if dest_dir == THISPC or not self.clipboard["paths"]:
            return
        for src in self.clipboard["paths"]:
            try:
                base = os.path.basename(src.rstrip(os.sep))
                dst = os.path.join(dest_dir, base)
                if self.clipboard["op"] == "copy":
                    if os.path.isdir(src):
                        shutil.copytree(src, dst)
                    else:
                        shutil.copy2(src, dst)
                elif self.clipboard["op"] == "cut":
                    shutil.move(src, dst)
            except (OSError, shutil.Error):
                pass
        if self.clipboard["op"] == "cut":
            self.clipboard = {"op": None, "paths": []}
        for p in self.panes:
            p.refresh()
    def do_move_to_other_side(self, pane_index, paths):
        dest = self.other_pane(pane_index).path
        if dest == THISPC:
            return
        moves = []
        for src in paths:
            try:
                dst = os.path.join(dest, os.path.basename(src.rstrip(os.sep)))
                shutil.move(src, dst)
                moves.append((src, dst))
            except (OSError, shutil.Error):
                pass
        self._record_move(moves)
        for p in self.panes:
            p.refresh()
    def do_copy_to_other_side(self, pane_index, paths):
        dest = self.other_pane(pane_index).path
        if dest == THISPC:
            return
        for src in paths:
            try:
                dst = os.path.join(dest, os.path.basename(src.rstrip(os.sep)))
                if os.path.isdir(src):
                    shutil.copytree(src, dst)
                else:
                    shutil.copy2(src, dst)
            except (OSError, shutil.Error):
                pass
        for p in self.panes:
            p.refresh()
    def do_delete(self, paths):
        recycle_bin_delete(paths)
        for p in self.panes:
            p.refresh()
    @staticmethod
    def open_with(choice, path):
        """Launch a file in a specific external app — the 'Open With...'
        submenu. 'Choose App' pops Windows' own Open-with dialog, so any
        installed program is reachable, not just the shortlist.

        Whenever a native Windows dialog is about to appear ('Choose App'),
        or a non-Meridian program is being launched, we also start the
        onscreenmenu overlay so the resulting window can be driven with a
        controller."""
        try:
            if not sys.platform.startswith("win"):
                subprocess.Popen(["xdg-open", path])
                return
            if choice == "Notepad":
                subprocess.Popen(["notepad.exe", path])
            elif choice == "WordPad":
                subprocess.Popen(["write.exe", path])
            elif choice == "Paint":
                subprocess.Popen(["mspaint.exe", path])
            elif choice == "Default App":
                # opening a non-Meridian program directly -> overlay too
                if _is_meridian_program(path):
                    Pane._launch_file(path)
                else:
                    launch_onscreenmenu()
                    Pane._launch_file(path)
            elif choice == "Choose App (Windows dialog)":
                # the native picker is a Windows dialog -> overlay to drive it
                launch_onscreenmenu()
                subprocess.Popen(["rundll32.exe", "shell32.dll,OpenAs_RunDLL", path])
        except Exception:
            pass

    @staticmethod
    def edit_in_notepad(path):
        try:
            if sys.platform.startswith("win"):
                subprocess.Popen(["notepad.exe", path])
            else:
                subprocess.Popen(["xdg-open", path])
        except Exception:
            pass
    def do_rename(self, old_path, new_name):
        new_path = os.path.join(os.path.dirname(old_path.rstrip(os.sep)), new_name)
        try:
            os.rename(old_path, new_path)
        except OSError:
            pass
    def do_change_extension(self, old_path, new_ext):
        if not new_ext.startswith("."):
            new_ext = "." + new_ext
        root, _ = os.path.splitext(old_path)
        try:
            os.rename(old_path, root + new_ext)
        except OSError:
            pass
    # ------------------------------------------------------------------ #
    # MENUS / POPUPS
    # ------------------------------------------------------------------ #
    def _build_view_submenu(self):
        cur = self.view_mode
        tm = self.theme_mode
        self.menu_options = [
            ("\u2022 " if cur == "text" else "") + "Text mode",
            ("\u2022 " if cur == "list" else "") + "List view",
            ("\u2022 " if cur == "icon" else "") + "Icon view",
            ("\u2022 " if cur == "gallery" else "") + "Gallery view",
            ("\u2022 " if tm == "system" else "") + "Theme: System",
            ("\u2022 " if tm == "day" else "") + "Theme: Day",
            ("\u2022 " if tm == "night" else "") + "Theme: Night",
            "Cancel",
        ]
        # strip the bullet prefix when matching choices later
        self.menu_options = [o.replace("\u2022 ", "") for o in self.menu_options]
        self.menu_selected = 0

    def _build_sort_submenu(self):
        self.menu_options = [
            "Sort by Name", "Sort by Size", "Sort by Type", "Sort by Date",
            "Ascending", "Descending", "Cancel",
        ]
        self.menu_selected = 0

    def _build_setbg_submenu(self, target):
        self._setbg_target = target
        self.menu_options = ["Background: Stretch", "Background: Center", "Cancel"]
        self.menu_selected = 0

    # ---- undo / redo of moves ------------------------------------------ #
    def _record_move(self, moves):
        """moves: list of (src, dst) that just happened. Pushed so Undo Move
        can reverse them (and Redo Move re-apply)."""
        if moves:
            self.undo_stack.append(moves)
            self.redo_stack.clear()

    def undo_move(self):
        if not self.undo_stack:
            self.set_flash("Nothing to undo")
            return
        moves = self.undo_stack.pop()
        reversed_moves = []
        for src, dst in moves:
            try:
                if os.path.exists(dst):
                    shutil.move(dst, src)
                    reversed_moves.append((src, dst))
            except (OSError, shutil.Error):
                pass
        if reversed_moves:
            self.redo_stack.append(reversed_moves)
        for p in self.panes:
            p.refresh()
        self.set_flash("Undid move")

    def redo_move(self):
        if not self.redo_stack:
            self.set_flash("Nothing to redo")
            return
        moves = self.redo_stack.pop()
        redone = []
        for src, dst in moves:
            try:
                if os.path.exists(src):
                    shutil.move(src, dst)
                    redone.append((src, dst))
            except (OSError, shutil.Error):
                pass
        if redone:
            self.undo_stack.append(redone)
        for p in self.panes:
            p.refresh()
        self.set_flash("Redid move")

    # ---- properties ----------------------------------------------------- #
    def _show_properties(self, path):
        """Populate a Windows-like properties view (shown as a popup)."""
        info = {}
        try:
            st = os.stat(path)
            info["Name"] = os.path.basename(path.rstrip(os.sep)) or path
            info["Location"] = os.path.dirname(path) or path
            info["Type"] = "Folder" if os.path.isdir(path) else (
                (_entry_ext(os.path.basename(path)).upper() + " file") if _entry_ext(os.path.basename(path)) else "File")
            if os.path.isdir(path):
                info["Size"] = "(folder)"
            else:
                info["Size"] = human_size(st.st_size)
            import datetime
            info["Modified"] = datetime.datetime.fromtimestamp(st.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
            info["Created"] = datetime.datetime.fromtimestamp(st.st_ctime).strftime("%Y-%m-%d %H:%M:%S")
            ro = not os.access(path, os.W_OK)
            info["Read-only"] = "Yes" if ro else "No"
        except OSError as e:
            info["Error"] = str(e)
        self.properties_info = info
        self.state = "properties"

    # ---- set image as launcher/explorer background ---------------------- #
    def _set_as_background(self, path, style):
        """Write the picked image + style into the Meridian Launcher settings
        so it becomes the launcher background. If the image later goes
        missing, the launcher already falls back to no custom background."""
        if not path or not os.path.isfile(path):
            self.set_flash("Image not found")
            return
        try:
            appdata = os.environ.get("LOCALAPPDATA", "")
            settings_path = os.path.join(appdata, "Meridian Launcher", "settings.json")
            data = {}
            if os.path.isfile(settings_path):
                with open(settings_path, "r", encoding="utf-8-sig") as f:
                    data = json.load(f)
            # store per-theme under the current/active layout if present, else
            # a generic key the launcher also understands
            layout = data.get("layout", "dawning_horizon")
            data.setdefault("background_by_theme", {})[layout] = path
            data["background_style"] = style  # "stretch" | "center"
            os.makedirs(os.path.dirname(settings_path), exist_ok=True)
            with open(settings_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            self.set_flash("Set as background (%s)" % style)
        except Exception as e:
            self.set_flash("Couldn't set background: %s" % e)

    def open_quick_access_menu(self):
        """The Quick Access rail has its own options menu — file operations
        that assume a directory listing don't apply here. Custom shortcuts the
        user added can be removed; the built-in entries (This PC, the user
        folders, drives) can't."""
        items = self.quick_access_items()
        if not items:
            return
        # Clamp rather than bail out: an out-of-range quick_selected (e.g.
        # after the rail's contents changed) previously meant this whole
        # function returned without ever setting self.state = "menu" - so
        # Start looked like it did nothing and the selector stayed stuck
        # on the file pane instead of moving into the popup.
        if not (0 <= self.quick_selected < len(items)):
            self.quick_selected = max(0, min(self.quick_selected, len(items) - 1))
        label, path = items[self.quick_selected]
        self.menu_options = ["Open", "Copy", "Cut", "Paste"]
        # only user-added shortcuts are removable
        if path not in ("__ADD__", THISPC) and path in self.quick_access:
            self.menu_options.append("Remove from List")
        self.menu_options.append("Cancel")
        self.menu_is_multi = False
        self.menu_selected = 0
        self.menu_pane_index = self.active_pane
        self.state = "menu"

    def open_options_menu(self):
        # The Quick Access rail is not a file listing — give it its own menu.
        if self.on_quick_rail():
            self.open_quick_access_menu()
            return
        pane = self.panes[self.active_pane]
        if self.multi_active:
            self.menu_options = ["Open"]
            if not self.single_pane and not self.three_pane:
                self.menu_options += ["Copy 2 Other Side", "Move 2 Other Side"]
            self.menu_options += [
                "Delete", "Rename", "Change File Extension", "Cancel",
            ]
            self.menu_is_multi = True
        else:
            if pane.current_entry() is None:
                # Empty area / no selection still offers global actions.
                self.menu_options = ["View...", "Sort...", "Search", "Select All", "Paste"]
                if self.undo_stack:
                    self.menu_options.append("Undo Move")
                if self.redo_stack:
                    self.menu_options.append("Redo Move")
                self.menu_options += ["Switch Pane Modes", "Exit Program", "Cancel"]
                self.menu_is_multi = False
                self.menu_selected = 0
                self.menu_pane_index = self.active_pane
                self.state = "menu"
                return
            entry = pane.current_entry()
            self.menu_options = ["Open"]
            if not entry.is_dir and not entry.is_drive:
                # "Edit" opens the built-in text editor; Notepad and other
                # external apps live under "Open With...".
                self.menu_options += ["Edit", "Hex Edit", "Open With..."]
                # Images get a "Set as Background" action.
                if _is_image_file(entry.name):
                    self.menu_options.append("Set as Background")
            self.menu_options += [
                "Copy", "Cut", "Paste", "Rename", "Change File Extension",
            ]
            # The "other side" actions only make sense with two real panes:
            # not in single-pane, and not in Quick Access (whose left column
            # is a shortcut rail, not a second listing).
            if not self.single_pane and not self.three_pane:
                self.menu_options += ["Move 2 Other Side", "Copy 2 Other Side"]
            self.menu_options += ["Delete", "Properties"]
            # Global view/sort/search/select/undo grouped at the bottom.
            self.menu_options += ["View...", "Sort...", "Search", "Select All"]
            if self.undo_stack:
                self.menu_options.append("Undo Move")
            if self.redo_stack:
                self.menu_options.append("Redo Move")
            self.menu_options += ["Switch Pane Modes", "Exit Program", "Cancel"]
            self.menu_is_multi = False
        self.menu_selected = 0
        self.menu_pane_index = self.active_pane
        self.state = "menu"
    def set_flash(self, msg, secs=3):
        self.flash_message = msg or ""
        self.flash_until = time.time() + secs

    def close_menu(self):
        self.state = "browse"
    def confirm_menu_selection(self):
        pane = self.panes[self.menu_pane_index]
        choice = self.menu_options[self.menu_selected]

        # Quick Access rail actions are handled separately — its entries are
        # shortcuts, not directory entries.
        if self.on_quick_rail():
            items = self.quick_access_items()
            label, path = items[self.quick_selected] if 0 <= self.quick_selected < len(items) else ("", "")
            if choice == "Open":
                self.activate_quick_access()
            elif choice == "Remove from List":
                if path in self.quick_access:
                    self.quick_access.remove(path)
                    self.quick_selected = max(0, self.quick_selected - 1)
                    self.save_state()
                    self.set_flash("Removed from Quick Access: " + label)
            elif choice in ("Copy", "Cut"):
                if path not in ("__ADD__", THISPC):
                    self.clipboard = {"op": choice.lower(), "paths": [path]}
                    self.set_flash("%s: %s" % (choice, label))
            elif choice == "Paste":
                if path not in ("__ADD__", THISPC) and os.path.isdir(path):
                    self.do_paste(path)
            self.close_menu()
            return

        targets = pane.multi_target_paths() if self.menu_is_multi else (
            [pane.full_path_of(pane.current_entry())] if pane.current_entry() else []
        )
        if choice == "Cancel":
            self.close_menu()
            return
        if choice == "Exit Program":
            # Meridian Launcher's watcher thread notices this process end
            # and moves the section selector back to the Sections bar,
            # restoring its own controls (see the Start-button comment
            # near handle_controller for the fuller explanation).
            self.running = False
            return
        if choice == "Switch Pane Modes":
            # Cycle: dual -> single -> quick access (rail + wide pane) -> dual
            if self.three_pane:
                self.three_pane = False
                self.single_pane = False
                msg = "Dual-pane mode"
            elif self.single_pane:
                self.single_pane = False
                self.three_pane = True
                self.active_pane = 1  # the wide main pane
                msg = "Quick Access mode"
            else:
                self.single_pane = True
                msg = "Single-pane mode"
            self.set_flash(msg)
            self.save_state()
            self.close_menu()
            return
        if choice == "Open":
            for path in targets:
                # Opening a non-Meridian executable brings up a normal
                # Windows window; start the overlay so it's controller-driven.
                if path.lower().endswith(".exe") and not _is_meridian_program(path):
                    launch_onscreenmenu()
                Pane._launch_file(path)  # static method, works for files/folders
            self.close_menu()
        elif choice == "Edit":
            self.close_menu()
            if targets:
                if run_text_editor is not None:
                    ok, err = run_text_editor(self, targets[0])
                    if not ok:
                        self.set_flash(err)
                else:
                    self.edit_in_notepad(targets[0])  # editors module missing
                self.panes[self.menu_pane_index].refresh()
        elif choice == "Hex Edit":
            self.close_menu()
            if targets:
                if run_hex_editor is not None:
                    ok, err = run_hex_editor(self, targets[0])
                    if not ok:
                        self.set_flash(err)
                else:
                    self.set_flash("Hex editor unavailable.")
                self.panes[self.menu_pane_index].refresh()
        elif choice == "Open With...":
            # swap the menu in place for the open-with submenu
            self._openwith_targets = targets
            self.menu_options = [
                "Notepad", "WordPad", "Paint", "Default App",
                "Choose App (Windows dialog)", "Cancel",
            ]
            self.menu_selected = 0
            return
        elif choice in ("Notepad", "WordPad", "Paint", "Default App",
                        "Choose App (Windows dialog)"):
            for path in getattr(self, "_openwith_targets", []):
                self.open_with(choice, path)
            self._openwith_targets = []
            self.close_menu()
        elif choice == "Copy":
            self.do_copy(targets)
            self.close_menu()
        elif choice == "Cut":
            self.do_cut(targets)
            self.close_menu()
        elif choice == "Paste":
            self.do_paste(pane.path)
            self.close_menu()
        elif choice == "Move 2 Other Side":
            self.do_move_to_other_side(self.menu_pane_index, targets)
            self._exit_multi_mode()
            self.close_menu()
        elif choice == "Copy 2 Other Side":
            self.do_copy_to_other_side(self.menu_pane_index, targets)
            self._exit_multi_mode()
            self.close_menu()
        elif choice == "Delete":
            self.pending_delete_paths = targets
            self.state = "confirm_delete"
        elif choice == "Rename":
            self.text_input_mode = "rename"
            self.text_input_queue = targets[1:] if len(targets) > 1 else []
            self.text_input_current = targets[0] if targets else None
            if self.text_input_current:
                self.text_input_value = os.path.basename(self.text_input_current.rstrip(os.sep))
                self.state = "text_input"
            else:
                self.close_menu()
        elif choice == "Change File Extension":
            self.text_input_mode = "extension"
            self.text_input_queue = targets[1:] if len(targets) > 1 else []
            self.text_input_current = targets[0] if targets else None
            if self.text_input_current:
                self.text_input_value = os.path.splitext(self.text_input_current)[1].lstrip('.')
                self.state = "text_input"
            else:
                self.close_menu()
        elif choice == "View...":
            # swap to the View submenu (view mode + day/night theme)
            self._build_view_submenu()
            return
        elif choice in ("Text mode", "List view", "Icon view", "Gallery view"):
            self.view_mode = {"Text mode": "text", "List view": "list",
                              "Icon view": "icon", "Gallery view": "gallery"}[choice]
            self.set_flash("View: " + choice)
            self.save_state()
            self.close_menu()
        elif choice in ("Theme: System", "Theme: Day", "Theme: Night"):
            self.theme_mode = choice.split(": ")[1].lower()
            apply_palette(self._effective_theme())
            self.set_flash("Theme: " + self.theme_mode)
            self.save_state()
            self.close_menu()
        elif choice == "Sort...":
            self._build_sort_submenu()
            return
        elif choice in ("Sort by Name", "Sort by Size", "Sort by Type", "Sort by Date"):
            self.sort_key = {"Sort by Name": "name", "Sort by Size": "size",
                             "Sort by Type": "type", "Sort by Date": "modified"}[choice]
            self.sync_sort()
            self.set_flash(choice)
            self.save_state()
            self.close_menu()
        elif choice in ("Ascending", "Descending"):
            self.sort_desc = (choice == "Descending")
            self.sync_sort()
            self.set_flash("Order: " + choice)
            self.save_state()
            self.close_menu()
        elif choice == "Select All":
            pane.multi_selected = set(range(len(pane.entries)))
            self.multi_active = True
            self.multi_pane_index = self.menu_pane_index
            self.set_flash("Selected all — B selects none")
            self.close_menu()
        elif choice == "Search":
            self.text_input_mode = "search"
            self.text_input_current = None
            self.text_input_value = ""
            self.state = "text_input"
        elif choice == "Undo Move":
            self.undo_move()
            self.close_menu()
        elif choice == "Redo Move":
            self.redo_move()
            self.close_menu()
        elif choice == "Properties":
            if targets:
                self._show_properties(targets[0])
            self.close_menu()
        elif choice == "Set as Background":
            if targets:
                self._build_setbg_submenu(targets[0])
            return
        elif choice in ("Background: Stretch", "Background: Center"):
            style = "stretch" if "Stretch" in choice else "center"
            self._set_as_background(getattr(self, "_setbg_target", None), style)
            self.close_menu()
        self.select_option()
    def confirm_delete(self, yes):
        if yes:
            self.do_delete(self.pending_delete_paths)
            self._exit_multi_mode()
        self.pending_delete_paths = []
        self.close_menu()
    def confirm_select_all(self, yes):
        if yes:
            pane = self.panes[self.active_pane]
            pane.select_all()
            self.multi_active = True
            self.multi_pane_index = self.active_pane
        self.state = "browse"
    def submit_text_input(self):
        if self.text_input_mode == "search":
            # Jump the active pane's selection to the first entry whose name
            # contains the query (case-insensitive). Leaves the view as-is if
            # nothing matches.
            query = (self.text_input_value or "").strip().lower()
            pane = self.panes[self.active_pane]
            if query:
                for i, e in enumerate(pane.entries):
                    if query in e.name.lower():
                        pane.selected = i
                        pane.scroll = max(0, i - 3)
                        self.set_flash("Found: " + e.name)
                        break
                else:
                    self.set_flash("No match for '%s'" % self.text_input_value)
            self.text_input_current = None
            self.text_input_mode = None
            self.state = "browse"
            return
        path = self.text_input_current
        if path:
            if self.text_input_mode == "rename":
                # Batch: apply same name to all remaining + current
                self.do_rename(path, self.text_input_value)
                for p in self.text_input_queue[:]:  # copy to avoid modification during iteration
                    self.do_rename(p, self.text_input_value)
                self.text_input_queue.clear()  # done with batch
            elif self.text_input_mode == "extension":
                # Batch: apply same extension to all
                self.do_change_extension(path, self.text_input_value)
                for p in self.text_input_queue[:]:
                    self.do_change_extension(p, self.text_input_value)
                self.text_input_queue.clear()
        self._advance_text_input_queue()
    def _advance_text_input_queue(self):
        for p in self.panes:
            p.refresh()
        if self.text_input_queue:
            self.text_input_current = self.text_input_queue.pop(0)
            if self.text_input_mode == "rename":
                self.text_input_value = os.path.basename(self.text_input_current.rstrip(os.sep))
            else:
                self.text_input_value = os.path.splitext(self.text_input_current)[1].lstrip('.')
        else:
            self.text_input_current = None
            self.state = "browse"
            self._exit_multi_mode()
    def _exit_multi_mode(self):
        if self.multi_active:
            self.panes[self.multi_pane_index].clear_multi()
        self.multi_active = False
        self.multi_pane_index = None
    # ------------------------------------------------------------------ #
    # INPUT: KEYBOARD
    # ------------------------------------------------------------------ #
    def handle_keyboard(self, event):
        if event.type != pygame.KEYDOWN:
            return
        # --- text entry popup swallows normal keys --- #
        if self.state == "text_input":
            if event.key == pygame.K_RETURN:
                self.submit_text_input()
            elif event.key == pygame.K_ESCAPE:
                self._advance_text_input_queue()
            elif event.key == pygame.K_BACKSPACE:
                self.text_input_value = self.text_input_value[:-1]
            elif event.unicode and event.unicode.isprintable():
                self.text_input_value += event.unicode
            return
        if self.state == "confirm_delete":
            if event.key in (pygame.K_RETURN, pygame.K_y):
                self.confirm_delete(True)
            elif event.key in (pygame.K_ESCAPE, pygame.K_n, pygame.K_BACKSPACE):
                self.confirm_delete(False)
            return
        if self.state == "confirm_selectall":
            if event.key in (pygame.K_RETURN, pygame.K_y):
                self.confirm_select_all(True)
            elif event.key in (pygame.K_ESCAPE, pygame.K_n, pygame.K_BACKSPACE):
                self.confirm_select_all(False)
            return
        if self.state == "properties":
            # any key dismisses the properties popup
            self.state = "browse"
            return
        if self.state == "menu":
            if event.key == pygame.K_UP:
                self.menu_selected = (self.menu_selected - 1) % len(self.menu_options)
            elif event.key == pygame.K_DOWN:
                self.menu_selected = (self.menu_selected + 1) % len(self.menu_options)
            elif event.key == pygame.K_RETURN:
                self.confirm_menu_selection()
            elif event.key in (pygame.K_ESCAPE, pygame.K_BACKSPACE):
                self.close_menu()
            return
        # --- normal browsing --- #
        pane = self.panes[self.active_pane]
        if event.key == pygame.K_ESCAPE:
            self.running = False
        elif event.key == pygame.K_UP:
            self.nav_vertical(-1)
        elif event.key == pygame.K_DOWN:
            self.nav_vertical(1)
        elif event.key == pygame.K_PAGEUP:
            pane.move(-5 * self.nav_columns())
        elif event.key == pygame.K_PAGEDOWN:
            pane.move(5 * self.nav_columns())
        elif event.key == pygame.K_LEFT:
            self.nav_horizontal(-1)
        elif event.key == pygame.K_TAB:
            self.switch_pane(1)
        elif event.key == pygame.K_RIGHT:
            self.nav_horizontal(1)
        elif event.key == pygame.K_RETURN:
            if self.on_quick_rail():
                self.activate_quick_access()
            elif self.multi_active and self.active_pane == self.multi_pane_index:
                pane.toggle_current_multi()
            else:
                pane.enter()
            self.select_option()
        elif event.key == pygame.K_BACKSPACE:
            if self.multi_active:
                self._exit_multi_mode()
            else:
                pane.go_up()
        elif event.key == pygame.K_m:
            self.open_options_menu()
        elif event.key == pygame.K_s:
            self._toggle_multi_mode_keyboard()
        elif event.key == pygame.K_r:
            self.state = "confirm_selectall"
        elif event.key == pygame.K_f:
            pane.reveal_in_explorer()
    def _toggle_multi_mode_keyboard(self):
        if self.multi_active:
            self._exit_multi_mode()
        else:
            self.multi_active = True
            self.multi_pane_index = self.active_pane
    # ------------------------------------------------------------------ #
    # INPUT: MOUSE
    # ------------------------------------------------------------------ #
    def pane_rects(self):
        pane_area_top = HEADER_HEIGHT + 16
        pane_area_h = self.height - HEADER_HEIGHT - FOOTER_HEIGHT - 32
        if self.three_pane:
            # Quick Access mode: a narrow left rail (1/6) + a wide main pane
            # (5/6). The left rail isn't a directory listing — it's the
            # shortcut list drawn by draw_quick_access().
            rail_w = (self.width - 3 * PANE_GAP) // 6
            main_w = self.width - 3 * PANE_GAP - rail_w
            rail = (PANE_GAP, pane_area_top, rail_w, pane_area_h)
            main = (PANE_GAP * 2 + rail_w, pane_area_top, main_w, pane_area_h)
            return [rail, main]
        if self.single_pane:
            # One pane fills the width; only the active pane is shown.
            full = (PANE_GAP, pane_area_top, self.width - 2 * PANE_GAP, pane_area_h)
            return [full, full]
        pane_w = (self.width - 3 * PANE_GAP) // 2
        left_rect = (PANE_GAP, pane_area_top, pane_w, pane_area_h)
        right_rect = (PANE_GAP * 2 + pane_w, pane_area_top, pane_w, pane_area_h)
        return [left_rect, right_rect]
    def row_index_at(self, pane, rect, mouse_pos):
        x, y, w, h = rect
        mx, my = mouse_pos
        if not (x <= mx <= x + w and y <= my <= y + h):
            return None
        list_top = y + 50
        if my < list_top:
            return None
        row = (my - list_top) // ROW_HEIGHT
        idx = pane.scroll + row
        if 0 <= idx < len(pane.entries):
            return idx
        return None
    def handle_mouse(self, event):
        if event.type != pygame.MOUSEBUTTONDOWN:
            return
        # Any popup open: clicks just act like Back except we keep it simple
        if self.state != "browse":
            if event.button == 3: # right click = back/cancel out of popups
                if self.state == "menu":
                    self.close_menu()
                elif self.state == "confirm_delete":
                    self.confirm_delete(False)
                elif self.state == "confirm_selectall":
                    self.confirm_select_all(False)
            return
        rects = self.pane_rects()
        for i, rect in enumerate(rects):
            pane = self.panes[i]
            idx = self.row_index_at(pane, rect, event.pos)
            if idx is None:
                continue
            if event.button == 1: # left click
                if not self.multi_active:
                    self.active_pane = i
                pane.selected = idx
                now = time.time()
                is_double = (
                    now - self._last_click_time < DOUBLE_CLICK_TIME
                    and self._last_click_pos == (i, idx)
                )
                self._last_click_time = now
                self._last_click_pos = (i, idx)
                if is_double:
                    if self.multi_active and i == self.multi_pane_index:
                        pane.toggle_current_multi()
                    else:
                        pane.enter()
                    self.select_option()
            elif event.button == 3: # right click = back
                if self.multi_active:
                    self._exit_multi_mode()
                else:
                    pane.go_up()
            return
    # ------------------------------------------------------------------ #
    # INPUT: CONTROLLER
    # ------------------------------------------------------------------ #
    def handle_controller(self):
        pane = self.panes[self.active_pane]
        for j in self.joysticks:
            num_buttons = j.get_numbuttons()
            def pressed(idx):
                return idx < num_buttons and j.get_button(idx)
            # ---- popup navigation takes priority ---- #
            if self.state == "text_input":
                # Text entry is keyboard-driven; controller just lets you
                # cancel out with B.
                if pressed(1) and self.cooldown.ready("c_back"):
                    self._advance_text_input_queue()
                continue
            if self.state == "confirm_delete":
                if pressed(0) and self.cooldown.ready("c_a", 1.0):
                    self.confirm_delete(True)
                elif pressed(1) and self.cooldown.ready("c_b"):
                    self.confirm_delete(False)
                continue
            if self.state == "confirm_selectall":
                if pressed(0) and self.cooldown.ready("c_a", 1.0):
                    self.confirm_select_all(True)
                elif pressed(1) and self.cooldown.ready("c_b"):
                    self.confirm_select_all(False)
                continue
            if self.state == "properties":
                if (pressed(0) or pressed(1)) and self.cooldown.ready("c_a", 0.5):
                    self.state = "browse"
                continue
            if self.state == "menu":
                if j.get_numhats() > 0:
                    _, hat_y = j.get_hat(0)
                    if hat_y == 1 and self.cooldown.ready("c_menu_up"):
                        self.menu_selected = (self.menu_selected - 1) % len(self.menu_options)
                    elif hat_y == -1 and self.cooldown.ready("c_menu_down"):
                        self.menu_selected = (self.menu_selected + 1) % len(self.menu_options)
                if j.get_numaxes() >= 2:
                    ax_y = j.get_axis(1)
                    if ax_y < -STICK_DEADZONE and self.cooldown.ready("c_menu_up"):
                        self.menu_selected = (self.menu_selected - 1) % len(self.menu_options)
                    elif ax_y > STICK_DEADZONE and self.cooldown.ready("c_menu_down"):
                        self.menu_selected = (self.menu_selected + 1) % len(self.menu_options)
                if pressed(0) and self.cooldown.ready("c_a", 1.0):
                    self.confirm_menu_selection()
                elif pressed(1) and self.cooldown.ready("c_b"):
                    self.close_menu()
                continue
            # ---- normal browsing ---- #
            if j.get_numhats() > 0:
                hat_x, hat_y = j.get_hat(0)
                if hat_y == 1 and self.cooldown.ready("dpad_up"):
                    self.nav_vertical(-1)
                elif hat_y == -1 and self.cooldown.ready("dpad_down"):
                    self.nav_vertical(1)
                if hat_x == -1 and self.cooldown.ready("dpad_left"):
                    self.nav_horizontal(-1)
                elif hat_x == 1 and self.cooldown.ready("dpad_right"):
                    self.nav_horizontal(1)
            if j.get_numaxes() >= 2:
                ax_x, ax_y = j.get_axis(0), j.get_axis(1)
                if ax_y < -STICK_DEADZONE and self.cooldown.ready("stick_up"):
                    self.nav_vertical(-1)
                elif ax_y > STICK_DEADZONE and self.cooldown.ready("stick_down"):
                    self.nav_vertical(1)
                if ax_x < -STICK_DEADZONE and self.cooldown.ready("stick_left"):
                    self.nav_horizontal(-1)
                elif ax_x > STICK_DEADZONE and self.cooldown.ready("stick_right"):
                    self.nav_horizontal(1)
            # ---- triggers: fast scroll (LT = up, RT = down) ---- #
            num_axes = j.get_numaxes()
            # LT (fast up)
            lt_pressed = False
            if num_axes > 2:
                lt = j.get_axis(2)
                if lt > TRIGGER_DEADZONE:
                    lt_pressed = True
            elif num_axes > 4:
                lt = j.get_axis(4)
                if lt > TRIGGER_DEADZONE:
                    lt_pressed = True
            if lt_pressed and self.cooldown.ready("lt_scroll", FAST_SCROLL_COOLDOWN):
                pane.move(-2)

            # RT (fast down)
            rt_pressed = False
            if num_axes > 5:
                rt = j.get_axis(5)
                if rt > TRIGGER_DEADZONE:
                    rt_pressed = True
            elif num_axes > 3:
                rt = j.get_axis(3)
                if rt > TRIGGER_DEADZONE:
                    rt_pressed = True
            if rt_pressed and self.cooldown.ready("rt_scroll", FAST_SCROLL_COOLDOWN):
                pane.move(2)
            # ---- face buttons ---- #
            if pressed(0) and self.cooldown.ready("btn_a", 1.0):
                if self.on_quick_rail():
                    self.activate_quick_access()
                elif self.multi_active and self.active_pane == self.multi_pane_index:
                    pane.toggle_current_multi()
                else:
                    pane.enter()
                self.select_option()
            if pressed(1) and self.cooldown.ready("btn_b"):
                if self.multi_active:
                    self._exit_multi_mode()
                else:
                    pane.go_up()
            if pressed(3) and self.cooldown.ready("btn_y"): # Y = options menu
                self.open_options_menu()
                # Control belongs to the menu from this instant on — skip the
                # rest of this frame's browse handling so the same press can't
                # also drive the file panes.
                continue
            if pressed(4) and self.cooldown.ready("btn_lb"):
                self.switch_pane(-1)
            if pressed(5) and self.cooldown.ready("btn_rb"):
                self.switch_pane(1)
            # ---- Back/Select held -> enter multi-select mode ---- #
            if pressed(6):
                if self._select_hold_start is None:
                    self._select_hold_start = time.time()
                elif (time.time() - self._select_hold_start >= SELECT_HOLD_TIME
                        and not self.multi_active and self.cooldown.ready("select_hold")):
                    self.multi_active = True
                    self.multi_pane_index = self.active_pane
            else:
                self._select_hold_start = None
            # ---- R3 (right stick click) -> select-all prompt ---- #
            if pressed(9) and self.cooldown.ready("btn_r3") and self.state == "browse":
                self.state = "confirm_selectall"
            if pressed(7) and self.cooldown.ready("btn_start"):
                # Start now moves the selector into the same options popup
                # Y opens, rather than quitting immediately - "Exit Program"
                # lives inside that popup as a selectable item instead.
                self.open_options_menu()
                continue
    # ------------------------------------------------------------------ #
    # DRAWING
    # ------------------------------------------------------------------ #
    def draw_header(self):
        pygame.draw.rect(self.screen, COL_HEADER_BG, (0, 0, self.width, HEADER_HEIGHT))
        title = self.font_title.render("MERIDIAN EXPLORER", True, COL_ACCENT)
        self.screen.blit(title, (30, 12))
        if self.multi_active:
            tag = "SELECT ALL MODE" if len(self.panes[self.multi_pane_index].multi_selected) == len(
                self.panes[self.multi_pane_index].entries) and self.panes[self.multi_pane_index].entries else "MULTI-SELECT MODE"
            tag_surf = self.font_row.render(tag, True, COL_MULTI_MARK)
            self.screen.blit(tag_surf, (30, 48))
        pygame.draw.line(self.screen, COL_PANE_BORDER, (0, HEADER_HEIGHT), (self.width, HEADER_HEIGHT), 2)
    def draw_footer(self):
        y = self.height - FOOTER_HEIGHT
        pygame.draw.rect(self.screen, COL_FOOTER_BG, (0, y, self.width, FOOTER_HEIGHT))
        pygame.draw.line(self.screen, COL_PANE_BORDER, (0, y), (self.width, y), 2)
        if self.multi_active:
            hints = "A: Toggle Select Y: Options B: Cancel Multi-Select"
        else:
            hints = "A: Confirm B: Back Y/Start: Options LB/RB: Switch Pane L-Stick R/RT: Fast Scroll Hold Select: Multi R3: Select All"
        text = self.font_footer.render(hints, True, COL_DIM_TEXT)
        self.screen.blit(text, (30, y + (FOOTER_HEIGHT - text.get_height()) // 2))
    def quick_access_items(self):
        """The Quick Access rail's entries (three-pane mode): This PC, the
        user's standard folders, any custom shortcuts the user added, then
        every currently-mounted drive. Returns [(label, path), ...]; entries
        whose folder is missing are skipped so the rail never shows dead
        links."""
        items = [("This PC", THISPC)]
        home = os.path.expanduser("~")
        for label, sub in (("Downloads", "Downloads"), ("Pictures", "Pictures"),
                           ("Videos", "Videos"), ("Documents", "Documents"),
                           ("Music", "Music")):
            p = os.path.join(home, sub)
            if os.path.isdir(p):
                items.append((label, p))
        # user-added custom shortcuts
        for p in self.quick_access:
            if os.path.isdir(p):
                items.append((os.path.basename(p.rstrip(os.sep)) or p, p))
        items.append(("+ Add current folder", "__ADD__"))
        # every mounted drive (Entry.name for drives is "C:\||Label")
        for e in list_windows_drives():
            drive = e.name.split("||")[0]
            label = e.name.split("||")[1] if "||" in e.name else drive
            items.append(("%s (%s)" % (drive, label) if label != drive else drive, drive))
        return items

    def activate_quick_access(self):
        """Open the highlighted Quick Access entry in the main (right) pane."""
        items = self.quick_access_items()
        if not (0 <= self.quick_selected < len(items)):
            return
        label, path = items[self.quick_selected]
        if path == "__ADD__":
            cur = self.panes[1].path
            if cur and cur != THISPC and cur not in self.quick_access:
                self.quick_access.append(cur)
                self.save_state()
                self.set_flash("Added to Quick Access: " + os.path.basename(cur.rstrip(os.sep)))
            return
        target = THISPC if path == THISPC else path
        if target != THISPC and not os.path.isdir(target):
            self.set_flash("Not available: " + label)
            return
        self.panes[1].path = target
        self.panes[1].selected = 0
        self.panes[1].scroll = 0
        self.panes[1].refresh()
        self.active_pane = 1

    def nav_columns(self):
        """Columns in the current pane's grid (1 in the row-based views), so
        up/down can step a whole row in icon/gallery mode."""
        if self.view_mode not in ("icon", "gallery"):
            return 1
        rects = self.pane_rects()
        _, _, w, _ = rects[self.active_pane]
        _, _, cols = self._grid_metrics(w)
        return max(1, cols)

    def on_quick_rail(self):
        """True when the Quick Access rail (three-pane mode's left column) is
        the focused pane — it navigates its shortcut list, not a listing."""
        return self.three_pane and self.active_pane == 0

    def nav_vertical(self, direction):
        """Up/down: one row — which is one entry in the list views and one
        full column-count step in the grid views."""
        if self.on_quick_rail():
            items = self.quick_access_items()
            if items:
                self.quick_selected = max(0, min(len(items) - 1, self.quick_selected + direction))
            return
        self.panes[self.active_pane].move(direction * self.nav_columns())

    def nav_horizontal(self, direction):
        """Left/right: in the grid views this moves within the row and only
        falls through to switching panes at the row edge. In the row-based
        views it always switches panes (the classic behavior)."""
        if self.three_pane:
            # rail <-> main pane
            self.active_pane = 1 if direction > 0 else 0
            return
        if self.view_mode not in ("icon", "gallery"):
            self.switch_pane(direction)
            return
        pane = self.panes[self.active_pane]
        cols = self.nav_columns()
        if not pane.entries:
            self.switch_pane(direction)
            return
        col = pane.selected % cols
        at_edge = (col == 0 and direction < 0) or (col == cols - 1 and direction > 0)
        if at_edge or (direction > 0 and pane.selected >= len(pane.entries) - 1):
            self.switch_pane(direction)
        else:
            pane.move(direction)

    def draw_quick_access(self, rect):
        """The left rail in three-pane mode — a Windows-Explorer-style Quick
        Access list rather than a directory listing. Fixed box, scrolls
        internally, driven by self.quick_selected."""
        x, y, w, h = rect
        is_active = (self.active_pane == 0)
        border_col = COL_ACTIVE_EDGE if is_active else COL_PANE_BORDER
        pygame.draw.rect(self.screen, COL_PANE_BG, rect, border_radius=10)
        pygame.draw.rect(self.screen, border_col, rect, width=3, border_radius=10)
        title = self.font_row.render("Quick Access", True, COL_ACCENT)
        self.screen.blit(title, (x + 14, y + 10))
        pygame.draw.line(self.screen, COL_PANE_BORDER, (x, y + 40), (x + w, y + 40), 1)
        items = self.quick_access_items()
        self.quick_selected = max(0, min(self.quick_selected, len(items) - 1))
        top = y + 50
        visible = max(1, (h - 60) // ROW_HEIGHT)
        first = getattr(self, "_qa_scroll", 0)
        if self.quick_selected < first:
            first = self.quick_selected
        elif self.quick_selected >= first + visible:
            first = self.quick_selected - visible + 1
        first = max(0, min(first, max(0, len(items) - visible)))
        self._qa_scroll = first
        clip = self.screen.get_clip()
        self.screen.set_clip(pygame.Rect(x + 4, top, w - 8, h - 60))
        for row in range(visible):
            i = first + row
            if i >= len(items):
                break
            label, path = items[i]
            row_y = top + row * ROW_HEIGHT
            if i == self.quick_selected:
                sel_col = COL_SELECT_BG if is_active else COL_SELECT_BG_INACTIVE
                pygame.draw.rect(self.screen, sel_col, (x + 6, row_y, w - 12, ROW_HEIGHT - 4), border_radius=6)
            col = COL_DRIVE if (path != "__ADD__" and (path == THISPC or len(path) <= 3)) else (
                COL_ACCENT if path == "__ADD__" else COL_FOLDER)
            pygame.draw.rect(self.screen, col, (x + 14, row_y + 10, 10, 10), border_radius=2)
            surf = self.font_row.render(label, True, COL_TEXT)
            maxw = w - 44
            if surf.get_width() > maxw:
                s = label
                while s and self.font_row.size(s + "\u2026")[0] > maxw:
                    s = s[:-1]
                surf = self.font_row.render(s + "\u2026", True, COL_TEXT)
            self.screen.blit(surf, (x + 32, row_y + 5))
        self.screen.set_clip(clip)

    def draw_pane(self, pane, index, rect):
        """Draw one pane's chrome (border + path header), then hand the
        listing area to the renderer for the current view mode:
          text    — name list with size column (the classic look)
          list    — small icon + name list
          icon    — medium icons in a grid
          gallery — large icons in a grid
        All four keep the pane box fixed and scroll internally, mirroring how
        the Launcher's list/gallery styles behave (minus theming)."""
        x, y, w, h = rect
        is_active = (index == self.active_pane)
        border_col = COL_ACTIVE_EDGE if is_active else COL_PANE_BORDER
        pygame.draw.rect(self.screen, COL_PANE_BG, rect, border_radius=10)
        pygame.draw.rect(self.screen, border_col, rect, width=3, border_radius=10)
        label = "This PC" if pane.path == THISPC else pane.path
        path_surf = self.font_row.render(label, True, COL_TEXT)
        max_w = w - 24
        if path_surf.get_width() > max_w:
            display_path = label
            while self.font_row.size(display_path)[0] > max_w and len(display_path) > 3:
                display_path = "..." + display_path[4:]
            path_surf = self.font_row.render(display_path, True, COL_TEXT)
        self.screen.blit(path_surf, (x + 14, y + 10))
        pygame.draw.line(self.screen, COL_PANE_BORDER, (x, y + 40), (x + w, y + 40), 1)
        if not pane.entries:
            empty = self.font_row.render("(empty)", True, COL_DIM_TEXT)
            self.screen.blit(empty, (x + 36, y + 56))
            return
        if self.view_mode in ("icon", "gallery"):
            self._draw_pane_grid(pane, index, rect, is_active)
        else:
            self._draw_pane_rows(pane, index, rect, is_active)

    def _entry_color(self, entry):
        if entry.is_drive:
            return COL_DRIVE
        return COL_FOLDER if entry.is_dir else COL_FILE

    def _draw_pane_rows(self, pane, index, rect, is_active):
        """text / list view: one entry per row. 'list' draws a larger icon
        block; 'text' keeps the original compact dot + size column."""
        x, y, w, h = rect
        big_icons = self.view_mode == "list"
        row_h = (ROW_HEIGHT + 10) if big_icons else ROW_HEIGHT
        list_top = y + 50
        visible_rows = max(1, (h - 60) // row_h)
        if pane.selected < pane.scroll:
            pane.scroll = pane.selected
        elif pane.selected >= pane.scroll + visible_rows:
            pane.scroll = pane.selected - visible_rows + 1
        max_scroll = max(0, len(pane.entries) - visible_rows)
        pane.scroll = max(0, min(pane.scroll, max_scroll))
        for row in range(visible_rows):
            i = pane.scroll + row
            if i >= len(pane.entries):
                break
            entry = pane.entries[i]
            row_y = list_top + row * row_h
            row_rect = (x + 6, row_y, w - 12, row_h - 4)
            if i in pane.multi_selected:
                pygame.draw.rect(self.screen, (60, 46, 24), row_rect, border_radius=6)
                pygame.draw.rect(self.screen, COL_MULTI_MARK, row_rect, width=2, border_radius=6)
            elif i == pane.selected:
                sel_col = COL_SELECT_BG if is_active else COL_SELECT_BG_INACTIVE
                pygame.draw.rect(self.screen, sel_col, row_rect, border_radius=6)
            icon_col = self._entry_color(entry)
            if big_icons:
                pygame.draw.rect(self.screen, icon_col, (x + 14, row_y + 7, 24, 24), border_radius=4)
                text_x = x + 48
            else:
                pygame.draw.rect(self.screen, icon_col, (x + 16, row_y + 10, 10, 10), border_radius=2)
                text_x = x + 36
            name_surf = self.font_row.render(pane.display_name_of(entry), True, COL_TEXT)
            self.screen.blit(name_surf, (text_x, row_y + (row_h - 4 - name_surf.get_height()) // 2))
            if not entry.is_dir and not entry.is_drive:
                size_surf = self.font_row.render(human_size(entry.size), True, COL_DIM_TEXT)
                self.screen.blit(size_surf, (x + w - size_surf.get_width() - 16,
                                             row_y + (row_h - 4 - size_surf.get_height()) // 2))

    def _grid_metrics(self, w):
        """Tile size + column count for the icon/gallery grids."""
        tile = 96 if self.view_mode == "icon" else 168  # gallery = large
        gap = 12
        cols = max(1, (w - gap) // (tile + gap))
        return tile, gap, cols

    def _draw_pane_grid(self, pane, index, rect, is_active):
        """icon / gallery view: tiles in a grid, scrolled internally by row —
        the same shape as the Launcher's gallery style."""
        x, y, w, h = rect
        tile, gap, cols = self._grid_metrics(w)
        cell_h = tile + 26  # tile + a caption line
        top = y + 50
        visible_rows = max(1, (h - 60) // cell_h)
        sel_row = pane.selected // cols
        first_row = pane.scroll // cols if cols else 0
        if sel_row < first_row:
            first_row = sel_row
        elif sel_row >= first_row + visible_rows:
            first_row = sel_row - visible_rows + 1
        total_rows = (len(pane.entries) + cols - 1) // cols
        first_row = max(0, min(first_row, max(0, total_rows - visible_rows)))
        pane.scroll = first_row * cols
        clip = self.screen.get_clip()
        self.screen.set_clip(pygame.Rect(x + 4, top, w - 8, h - 60))
        for r in range(visible_rows):
            for cidx in range(cols):
                i = (first_row + r) * cols + cidx
                if i >= len(pane.entries):
                    break
                entry = pane.entries[i]
                cx = x + gap + cidx * (tile + gap)
                cy = top + r * cell_h
                cell = pygame.Rect(cx, cy, tile, tile)
                if i in pane.multi_selected:
                    pygame.draw.rect(self.screen, (60, 46, 24), cell.inflate(8, 8), border_radius=8)
                    pygame.draw.rect(self.screen, COL_MULTI_MARK, cell.inflate(8, 8), width=2, border_radius=8)
                elif i == pane.selected:
                    sel_col = COL_SELECT_BG if is_active else COL_SELECT_BG_INACTIVE
                    pygame.draw.rect(self.screen, sel_col, cell.inflate(8, 8), border_radius=8)
                pygame.draw.rect(self.screen, self._entry_color(entry), cell, border_radius=8)
                name = pane.display_name_of(entry)
                surf = self.font_footer.render(name, True, COL_TEXT)
                if surf.get_width() > tile:
                    s = name
                    while s and self.font_footer.size(s + "\u2026")[0] > tile:
                        s = s[:-1]
                    surf = self.font_footer.render(s + "\u2026", True, COL_TEXT)
                self.screen.blit(surf, (cx + (tile - surf.get_width()) // 2, cy + tile + 4))
        self.screen.set_clip(clip)
    def draw_popup_box(self, title, width, height):
        x = (self.width - width) // 2
        y = (self.height - height) // 2
        rect = (x, y, width, height)
        pygame.draw.rect(self.screen, COL_POPUP_BG, rect, border_radius=12)
        pygame.draw.rect(self.screen, COL_POPUP_BORDER, rect, width=3, border_radius=12)
        title_surf = self.font_popup.render(title, True, COL_ACCENT)
        self.screen.blit(title_surf, (x + (width - title_surf.get_width()) // 2, y + 16))
        return x, y, width, height
    def draw_menu(self):
        overlay = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 140))
        self.screen.blit(overlay, (0, 0))
        item_h = 44
        width = 420
        height = 70 + item_h * len(self.menu_options)
        x, y, w, h = self.draw_popup_box("OPTIONS", width, height)
        for i, opt in enumerate(self.menu_options):
            row_y = y + 60 + i * item_h
            row_rect = (x + 16, row_y, w - 32, item_h - 8)
            if i == self.menu_selected:
                pygame.draw.rect(self.screen, COL_POPUP_ITEM_HL, row_rect, border_radius=8)
            color = COL_DANGER if opt == "Delete" else COL_TEXT
            text = self.font_row.render(opt, True, color)
            self.screen.blit(text, (row_rect[0] + 16, row_y + (item_h - 8 - text.get_height()) // 2))
    def draw_confirm(self, title, yes_no_hint):
        overlay = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 140))
        self.screen.blit(overlay, (0, 0))
        x, y, w, h = self.draw_popup_box(title, 480, 160)
        hint_surf = self.font_row.render(yes_no_hint, True, COL_DIM_TEXT)
        self.screen.blit(hint_surf, (x + (w - hint_surf.get_width()) // 2, y + 90))
    def draw_text_input(self):
        overlay = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 140))
        self.screen.blit(overlay, (0, 0))
        title = "Rename" if self.text_input_mode == "rename" else "Change File Extension"
        x, y, w, h = self.draw_popup_box(title, 560, 170)
        box_rect = (x + 30, y + 70, w - 60, 44)
        pygame.draw.rect(self.screen, COL_PANE_BG, box_rect, border_radius=8)
        pygame.draw.rect(self.screen, COL_ACCENT, box_rect, width=2, border_radius=8)
        val_surf = self.font_row.render(self.text_input_value + "|", True, COL_TEXT)
        self.screen.blit(val_surf, (box_rect[0] + 10, box_rect[1] + (44 - val_surf.get_height()) // 2))
        hint = self.font_footer.render("Enter: Confirm Esc/B: Skip", True, COL_DIM_TEXT)
        self.screen.blit(hint, (x + (w - hint.get_width()) // 2, y + h - 34))
    def draw_properties(self):
        overlay = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 140))
        self.screen.blit(overlay, (0, 0))
        info = getattr(self, "properties_info", {}) or {}
        rows = list(info.items())
        height = 90 + 30 * len(rows)
        x, y, w, h = self.draw_popup_box("PROPERTIES", 560, height)
        ry = y + 60
        for label, val in rows:
            lab = self.font_row.render(str(label) + ":", True, COL_DIM_TEXT)
            self.screen.blit(lab, (x + 30, ry))
            v = self.font_row.render(str(val), True, COL_TEXT)
            # clip long values to the box width
            maxw = w - 210
            if v.get_width() > maxw:
                s = str(val)
                while s and self.font_row.size(s + "\u2026")[0] > maxw:
                    s = s[:-1]
                v = self.font_row.render(s + "\u2026", True, COL_TEXT)
            self.screen.blit(v, (x + 190, ry))
            ry += 30
        hint = self.font_footer.render("Any key / A / B: close", True, COL_DIM_TEXT)
        self.screen.blit(hint, (x + (w - hint.get_width()) // 2, y + h - 32))

    def draw(self):
        self.screen.fill(COL_BG)
        self.draw_header()
        rects = self.pane_rects()
        if self.three_pane:
            # left = Quick Access rail, right = the wide main listing
            self.draw_quick_access(rects[0])
            self.draw_pane(self.panes[1], 1, rects[1])
        elif self.single_pane:
            self.draw_pane(self.panes[self.active_pane], self.active_pane, rects[self.active_pane])
        else:
            self.draw_pane(self.panes[0], 0, rects[0])
            self.draw_pane(self.panes[1], 1, rects[1])
        self.draw_footer()
        if self.state == "menu":
            self.draw_menu()
        elif self.state == "confirm_delete":
            n = len(self.pending_delete_paths)
            self.draw_confirm(f"Send {n} item(s) to Recycle Bin?", "A / Enter: Yes B / Esc: No")
        elif self.state == "confirm_selectall":
            self.draw_confirm("Select All Files In This Folder?", "A / Enter: Yes B / Esc: No")
        elif self.state == "text_input":
            self.draw_text_input()
        elif self.state == "properties":
            self.draw_properties()
        if self.flash_message and time.time() < self.flash_until:
            surf = self.font_footer.render(self.flash_message, True, (255, 220, 120))
            self.screen.blit(surf, (self.width // 2 - surf.get_width() // 2, self.height - 60))
        pygame.display.flip()
    # ------------------------------------------------------------------ #
    # MAIN LOOP
    # ------------------------------------------------------------------ #
    def run(self):
        while self.running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                elif event.type == pygame.KEYDOWN:
                    self.handle_keyboard(event)
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    self.handle_mouse(event)
            self.handle_controller()
            self.draw()
            self.clock.tick(60)
        self.save_state()
        pygame.quit()
def _parse_box_arg():
    """Looks for a --box=X,Y,W,H argument (screen coordinates Meridian
    Launcher wants this window sized/positioned to). Returns a
    (x, y, w, h) tuple of ints, or None if absent/malformed."""
    for arg in sys.argv[1:]:
        if arg.startswith("--box="):
            try:
                parts = [int(p) for p in arg[len("--box="):].split(",")]
                if len(parts) == 4:
                    return tuple(parts)
            except ValueError:
                pass
    return None


def _start_path_from_argv():
    """Folder to open, from the command line — how Windows hands us the
    path when Meridian Explorer is registered as a folder handler
    ("...\\Meridian Explorer.exe" "%1") or when another Meridian app routes
    a folder open here. A file path is accepted too and resolves to its
    containing folder. Returns None when there's nothing usable, so plain
    double-click launches behave exactly as before."""
    path_args = [a for a in sys.argv[1:] if not a.startswith("--box=")]
    if not path_args:
        return None
    raw = " ".join(path_args).strip().strip('"')
    if raw.lower().startswith("file:///"):  # some callers hand over file URLs
        from urllib.parse import unquote
        raw = unquote(raw[8:]).replace("/", "\\")
    if not raw:
        return None
    if os.path.isdir(raw):
        return raw
    if os.path.isfile(raw):
        return os.path.dirname(raw) or None
    return None


if __name__ == "__main__":
    MeridianExplorer(start_path=_start_path_from_argv(), box=_parse_box_arg()).run()
