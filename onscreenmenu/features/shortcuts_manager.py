"""
onscreenmenu Shortcuts Manager (Y button)

The Y menu always starts with "Meridian Launcher" (fixed, cannot
be removed), followed by up to MAX_CUSTOM_SHORTCUTS user-added
shortcuts, followed by "Add Shortcut" / "Remove Shortcut".
"""

import os
import subprocess
import sys

import psutil
import win32con
import win32gui
import win32process


def _onscreenmenu_dir():
    """Folder onscreenmenu.exe (or, when run from source, main.py) actually
    lives in."""

    if getattr(sys, "frozen", False):

        return os.path.dirname(os.path.abspath(sys.executable))

    return os.path.dirname(os.path.abspath(sys.argv[0]))


MERIDIAN_LABEL = "Meridian Launcher"

MERIDIAN_EXE_NAME = "MeridianLauncher.exe"

# All five Meridian .exe's (MeridianLauncher.exe, onscreenmenu.exe,
# CyberDeckBrowser.exe, "Meridian Explorer.exe", "Meridian Game
# Library.exe") are deployed flat in the same install folder - see
# osm.bat, which launches onscreenmenu.exe via "%~dp0onscreenmenu.exe".
# So MeridianLauncher.exe sits right next to onscreenmenu.exe itself.
MERIDIAN_PATH = os.path.join(
    _onscreenmenu_dir(),
    MERIDIAN_EXE_NAME
)

MERIDIAN_ERROR_MESSAGE = (
    "Hey! Move MeridianLauncher.exe back to "
    "the local folder you psychopath!"
)

MAX_CUSTOM_SHORTCUTS = 11

MAX_NAME_LENGTH = 20


class ShortcutsManager:


    def __init__(
        self,
        config,
        save_config_fn
    ):

        self.config = config

        self.save_config_fn = save_config_fn

        if "shortcuts" not in self.config:

            self.config["shortcuts"] = []


    #
    # ---- data ----
    #

    @property
    def custom(self):

        return self.config["shortcuts"]


    def menu_items(self):

        return (

            [MERIDIAN_LABEL]

            +

            [entry["name"] for entry in self.custom]

            +

            ["Add Shortcut", "Remove Shortcut"]

        )


    def can_add(self):

        return len(self.custom) < MAX_CUSTOM_SHORTCUTS


    def add(
        self,
        name,
        path
    ):

        name = name.strip()[:MAX_NAME_LENGTH]

        if not name or not path:

            return False

        self.custom.append(
            {
                "name": name,
                "path": path
            }
        )

        self.save_config_fn(
            self.config
        )

        return True


    def remove(
        self,
        name
    ):

        self.config["shortcuts"] = [

            entry
            for entry in self.custom
            if entry["name"] != name

        ]

        self.save_config_fn(
            self.config
        )


    def path_for(
        self,
        name
    ):

        for entry in self.custom:

            if entry["name"] == name:

                return entry["path"]

        return None


    #
    # ---- running a shortcut ----
    #

    def run(
        self,
        name,
        error_cb=None
    ):

        if name == MERIDIAN_LABEL:

            self._run_meridian(
                error_cb
            )

            return

        path = self.path_for(name)

        if not path or not os.path.exists(path):

            if error_cb:

                error_cb(
                    '"' + name + '" could not be found. '
                    "It may have been moved or deleted."
                )

            return

        try:

            os.startfile(path)

        except Exception as error:

            if error_cb:

                error_cb(
                    'Could not open "' + name + '": ' + str(error)
                )


    def _run_meridian(
        self,
        error_cb
    ):

        pid = self._find_pid(
            MERIDIAN_EXE_NAME
        )

        if pid:

            self._focus_pid(pid)

            return

        if os.path.isfile(MERIDIAN_PATH):

            try:

                subprocess.Popen(
                    [MERIDIAN_PATH]
                )

            except Exception as error:

                if error_cb:

                    error_cb(
                        "Couldn't launch MeridianLauncher.exe: "
                        + str(error)
                    )

            return

        if error_cb:

            error_cb(
                MERIDIAN_ERROR_MESSAGE
            )


    def _find_pid(
        self,
        exe_name
    ):

        for proc in psutil.process_iter(["pid", "name"]):

            try:

                name = proc.info.get("name")

                if name and name.lower() == exe_name.lower():

                    return proc.info["pid"]

            except (psutil.NoSuchProcess, psutil.AccessDenied):

                continue

        return None


    def _focus_pid(
        self,
        pid
    ):

        result = {"hwnd": None}

        def enum_handler(hwnd, _):

            if result["hwnd"] is not None:

                return True

            if not win32gui.IsWindowVisible(hwnd):

                return True

            _, found_pid = win32process.GetWindowThreadProcessId(hwnd)

            if found_pid == pid and win32gui.GetWindowText(hwnd):

                result["hwnd"] = hwnd

            return True

        try:

            win32gui.EnumWindows(
                enum_handler,
                None
            )

        except Exception:

            pass

        hwnd = result["hwnd"]

        if not hwnd:

            return

        try:

            win32gui.ShowWindow(
                hwnd,
                win32con.SW_RESTORE
            )

            win32gui.SetForegroundWindow(hwnd)

        except Exception:

            pass
