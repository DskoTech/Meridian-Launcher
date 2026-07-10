import os
import sys
import json
import time
import shutil
import string
import ctypes
import subprocess
import collections
# Prevent the fullscreen pygame window from auto-minimizing when it loses
# OS focus (e.g. when the Y-menu "Edit"/"Open" actions launch Notepad or
# another external app). Without this, the window drops to the background
# and stops receiving controller/keyboard input until manually restored.
os.environ.setdefault("SDL_VIDEO_MINIMIZE_ON_FOCUS_LOSS", "0")
import pygame
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
STATE_FILE = os.path.join(os.path.expanduser("~"), ".meridian_explorer_state.json")
INSTALL_DIR = r"C:\Program Files\DskoTech"
# --- Color palette: dark "console" theme --------------------------------- #
COL_BG = (14, 16, 22)
COL_PANE_BG = (22, 25, 34)
COL_PANE_BORDER = (40, 44, 58)
COL_ACTIVE_EDGE = (90, 200, 255)
COL_TEXT = (225, 228, 235)
COL_DIM_TEXT = (130, 136, 150)
COL_FOLDER = (255, 205, 100)
COL_FILE = (170, 200, 230)
COL_DRIVE = (140, 230, 170)
COL_SELECT_BG = (46, 100, 140)
COL_SELECT_BG_INACTIVE = (34, 38, 50)
COL_MULTI_MARK = (255, 150, 60)
COL_HEADER_BG = (18, 20, 28)
COL_FOOTER_BG = (18, 20, 28)
COL_ACCENT = (90, 200, 255)
COL_POPUP_BG = (26, 29, 40)
COL_POPUP_BORDER = (90, 200, 255)
COL_POPUP_ITEM_HL = (46, 100, 140)
COL_DANGER = (230, 90, 90)
Entry = collections.namedtuple("Entry", "name is_dir size is_drive")
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
def check_install_location():
    """
    On Windows, verify the running file (script or frozen exe) lives in
    C:\\Program Files\\DskoTech\\. If not, prompt the user with a native
    Yes/No message box offering to copy it there. Runs before pygame is
    initialized, so it uses the plain Win32 MessageBox API.
    """
    if not sys.platform.startswith("win"):
        return
    try:
        current_path = os.path.abspath(
            sys.executable if getattr(sys, "frozen", False) else os.path.abspath(__file__)
        )
    except NameError:
        return
    current_dir = os.path.dirname(current_path)
    if os.path.normcase(os.path.normpath(current_dir)) == os.path.normcase(os.path.normpath(INSTALL_DIR)):
        return
    MB_YESNO = 0x04
    MB_ICONQUESTION = 0x20
    MB_ICONWARNING = 0x30
    MB_TOPMOST = 0x40000
    IDYES = 6
    message = (
        "Meridian Explorer is not in C:\\Program Files\\DskoTech\\, "
        "you can run it elsewhere, but it will cause errors if it's not there, "
        "would you like to make a copy there?"
    )
    result = ctypes.windll.user32.MessageBoxW(
        0, message, "Meridian Explorer", MB_YESNO | MB_ICONQUESTION | MB_TOPMOST
    )
    if result != IDYES:
        return
    try:
        os.makedirs(INSTALL_DIR, exist_ok=True)
        dest = os.path.join(INSTALL_DIR, os.path.basename(current_path))
        shutil.copy2(current_path, dest)
        ctypes.windll.user32.MessageBoxW(
            0, f"Copied to {dest}", "Meridian Explorer", MB_TOPMOST
        )
    except OSError as e:
        ctypes.windll.user32.MessageBoxW(
            0, f"Copy failed: {e}", "Meridian Explorer", MB_ICONWARNING | MB_TOPMOST
        )
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
        dirs.sort(key=lambda e: e.name.lower())
        files.sort(key=lambda e: e.name.lower())
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
            drive, label = entry.name.split("||")
            return f"{drive} ({label})"
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
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("Meridian Explorer")
        info = pygame.display.Info()
        self.width, self.height = info.current_w, info.current_h
        self.screen = pygame.display.set_mode((self.width, self.height), pygame.FULLSCREEN)
        self.clock = pygame.time.Clock()
        self.cooldown = Cooldown(COOLDOWN)
        self.font_header = pygame.font.SysFont(FONT_NAME, 26, bold=True)
        self.font_row = pygame.font.SysFont(FONT_NAME, 19)
        self.font_footer = pygame.font.SysFont(FONT_NAME, 17)
        self.font_title = pygame.font.SysFont(FONT_NAME, 30, bold=True)
        self.font_popup = pygame.font.SysFont(FONT_NAME, 22)
        left_path, right_path = self.load_state()
        self.panes = [Pane(left_path), Pane(right_path)]
        self.active_pane = 0
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
        self._last_click_time = 0
        self._last_click_pos = None
        pygame.joystick.init()
        self.joysticks = [pygame.joystick.Joystick(i) for i in range(pygame.joystick.get_count())]
        for j in self.joysticks:
            j.init()
        self.running = True
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
    def save_state(self):
        try:
            with open(STATE_FILE, "w", encoding="utf-8") as f:
                json.dump({"left": self.panes[0].path, "right": self.panes[1].path}, f)
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
        for src in paths:
            try:
                shutil.move(src, os.path.join(dest, os.path.basename(src.rstrip(os.sep))))
            except (OSError, shutil.Error):
                pass
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
    def open_options_menu(self):
        pane = self.panes[self.active_pane]
        if self.multi_active:
            self.menu_options = [
                "Open", "Copy 2 Other Side", "Move 2 Other Side",
                "Delete", "Rename", "Change File Extension", "Cancel",
            ]
            self.menu_is_multi = True
        else:
            if pane.current_entry() is None:
                return
            entry = pane.current_entry()
            self.menu_options = ["Open"]
            if not entry.is_dir and not entry.is_drive:
                self.menu_options.append("Edit")
            self.menu_options += [
                "Copy", "Cut", "Paste", "Rename", "Change File Extension",
                "Move 2 Other Side", "Copy 2 Other Side", "Delete", "Cancel",
            ]
            self.menu_is_multi = False
        self.menu_selected = 0
        self.menu_pane_index = self.active_pane
        self.state = "menu"
    def close_menu(self):
        self.state = "browse"
    def confirm_menu_selection(self):
        pane = self.panes[self.menu_pane_index]
        choice = self.menu_options[self.menu_selected]
        targets = pane.multi_target_paths() if self.menu_is_multi else (
            [pane.full_path_of(pane.current_entry())] if pane.current_entry() else []
        )
        if choice == "Cancel":
            self.close_menu()
            return
        if choice == "Open":
            for path in targets:
                Pane._launch_file(path)  # static method, works for files/folders
            self.close_menu()
        elif choice == "Edit":
            for path in targets:
                self.edit_in_notepad(path)
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
            pane.move(-1)
        elif event.key == pygame.K_DOWN:
            pane.move(1)
        elif event.key == pygame.K_PAGEUP:
            pane.move(-5)
        elif event.key == pygame.K_PAGEDOWN:
            pane.move(5)
        elif event.key == pygame.K_LEFT:
            self.switch_pane(-1)
        elif event.key in (pygame.K_RIGHT, pygame.K_TAB):
            self.switch_pane(1)
        elif event.key == pygame.K_RETURN:
            if self.multi_active and self.active_pane == self.multi_pane_index:
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
                    pane.move(-1)
                elif hat_y == -1 and self.cooldown.ready("dpad_down"):
                    pane.move(1)
                if hat_x == -1 and self.cooldown.ready("dpad_left"):
                    self.switch_pane(-1)
                elif hat_x == 1 and self.cooldown.ready("dpad_right"):
                    self.switch_pane(1)
            if j.get_numaxes() >= 2:
                ax_x, ax_y = j.get_axis(0), j.get_axis(1)
                if ax_y < -STICK_DEADZONE and self.cooldown.ready("stick_up"):
                    pane.move(-1)
                elif ax_y > STICK_DEADZONE and self.cooldown.ready("stick_down"):
                    pane.move(1)
                if ax_x < -STICK_DEADZONE and self.cooldown.ready("stick_left"):
                    self.switch_pane(-1)
                elif ax_x > STICK_DEADZONE and self.cooldown.ready("stick_right"):
                    self.switch_pane(1)
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
                if self.multi_active and self.active_pane == self.multi_pane_index:
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
                self.running = False
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
            hints = "A: Confirm B: Back Y: Options LB/RB: Switch Pane L-Stick R/RT: Fast Scroll Hold Select: Multi R3: Select All Start: Quit"
        text = self.font_footer.render(hints, True, COL_DIM_TEXT)
        self.screen.blit(text, (30, y + (FOOTER_HEIGHT - text.get_height()) // 2))
    def draw_pane(self, pane, index, rect):
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
        list_top = y + 50
        visible_rows = max(1, (h - 60) // ROW_HEIGHT)
        if pane.selected < pane.scroll:
            pane.scroll = pane.selected
        elif pane.selected >= pane.scroll + visible_rows:
            pane.scroll = pane.selected - visible_rows + 1
        # Clamp scroll to valid range
        max_scroll = max(0, len(pane.entries) - visible_rows)
        pane.scroll = max(0, min(pane.scroll, max_scroll))
        for row in range(visible_rows):
            i = pane.scroll + row
            if i >= len(pane.entries):
                break
            entry = pane.entries[i]
            row_y = list_top + row * ROW_HEIGHT
            row_rect = (x + 6, row_y, w - 12, ROW_HEIGHT - 4)
            if i in pane.multi_selected:
                pygame.draw.rect(self.screen, (60, 46, 24), row_rect, border_radius=6)
                pygame.draw.rect(self.screen, COL_MULTI_MARK, row_rect, width=2, border_radius=6)
            elif i == pane.selected:
                sel_col = COL_SELECT_BG if is_active else COL_SELECT_BG_INACTIVE
                pygame.draw.rect(self.screen, sel_col, row_rect, border_radius=6)
            if entry.is_drive:
                icon_col = COL_DRIVE
            elif entry.is_dir:
                icon_col = COL_FOLDER
            else:
                icon_col = COL_FILE
            pygame.draw.rect(self.screen, icon_col, (x + 16, row_y + 10, 10, 10), border_radius=2)
            name_surf = self.font_row.render(pane.display_name_of(entry), True, COL_TEXT)
            self.screen.blit(name_surf, (x + 36, row_y + 5))
            if not entry.is_dir and not entry.is_drive:
                size_surf = self.font_row.render(human_size(entry.size), True, COL_DIM_TEXT)
                self.screen.blit(size_surf, (x + w - size_surf.get_width() - 16, row_y + 5))
        if not pane.entries:
            empty = self.font_row.render("(empty)", True, COL_DIM_TEXT)
            self.screen.blit(empty, (x + 36, list_top + 6))
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
    def draw(self):
        self.screen.fill(COL_BG)
        self.draw_header()
        rects = self.pane_rects()
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
if __name__ == "__main__":
    check_install_location()
    MeridianExplorer().run()
