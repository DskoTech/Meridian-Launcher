"""
onscreenmenu Entry Point
"""

import os
import sys
import traceback

from crash_logger import install_crash_logging
install_crash_logging("onscreenmenu")

try:

    import psutil

except ImportError:

    psutil = None

from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtCore import Qt

from config import load_config, save_config, _config_dir

from features import startup

from ui.main_window import MainWindow


EXE_NAME = "onscreenmenu.exe"


def _another_instance_already_running():
    """Checks whether a different process is already running
    onscreenmenu.exe, so a second launch (e.g. from a shortcut/macro that
    fires even though it's already open) can quietly bow out instead of
    running two overlays at once.

    A PyInstaller --onefile build's bootloader briefly runs as its OWN
    process (that also shows up named "onscreenmenu.exe") before it
    extracts and execs the real app as a child - so on every single
    compiled launch, there are two "onscreenmenu.exe" processes alive for
    a moment: the bootloader (this process's parent) and this process
    itself. Only skipping my_pid missed that, so this check saw its own
    bootloader parent and concluded "another instance is already running"
    every time, immediately exiting - which is exactly why it looked like
    onscreenmenu "doesn't run" once compiled, despite working fine from
    source (where the process is named python.exe/pythonw.exe, never
    triggering this path at all). Skipping the parent PID too fixes it."""

    if psutil is None:

        return False

    my_pid = os.getpid()
    my_parent_pid = os.getppid()

    try:

        for proc in psutil.process_iter(["pid", "name"]):

            try:

                if proc.pid in (my_pid, my_parent_pid):

                    continue

                name = proc.info.get("name")

                if name and name.lower() == EXE_NAME.lower():

                    return True

            except (psutil.NoSuchProcess, psutil.AccessDenied):

                continue

    except Exception:

        return False

    return False


def _crash_log_path():

    return os.path.join(
        _config_dir(),
        "crash.log"
    )


def _write_crash_log(exc_text):

    try:

        os.makedirs(
            _config_dir(),
            exist_ok=True
        )

        with open(_crash_log_path(), "a") as f:

            f.write(exc_text + "\n\n")

    except Exception:

        pass


def main():

    #
    # Single-instance guard: if another onscreenmenu.exe is already
    # running, this one quietly exits instead of running a second
    # overlay/cursor/hotkey stack alongside it.
    #

    if _another_instance_already_running():

        sys.exit(0)

    Qt.HighDpiScaleFactorRoundingPolicy.PassThrough

    app = QApplication(sys.argv)

    #
    # onscreenmenu opens and closes several of its own dialogs
    # (install prompt, first-run instructions, message boxes,
    # popup menus) throughout its life, including BEFORE the main
    # window exists. Qt's default is to quit the whole app the
    # instant zero top-level windows are visible - which would
    # otherwise fire the moment one of those early dialogs closes,
    # then actually take effect as soon as the real event loop
    # (app.exec() below) starts, closing the app right after the
    # main window appears. onscreenmenu manages its own lifetime
    # explicitly (Ctrl+T, L3+R3, closing the main window), so this
    # automatic behavior is turned off.
    #

    app.setQuitOnLastWindowClosed(False)

    config = load_config()

    #
    # Meridian Launcher (or osm.bat) passes --window-mode=borderless-
    # fullscreen when it starts this app, asking for windowed (borderless)
    # fullscreen for this run regardless of whatever was last saved. This
    # only affects the in-memory config for this run - never written back
    # to disk, so a person's own saved preference survives the next launch.
    #

    if "--window-mode=borderless-fullscreen" in sys.argv:

        config["fullscreen"] = True

    #
    # 1. "Wrong place" install prompt (only does anything for a
    #    built exe, and only once unless the person says yes)
    #

    startup.maybe_prompt_install(
        config,
        save_config
    )

    #
    # 2. Splash screen
    #

    startup.show_splash(app)

    #
    # 3. First-run instructions (shown once, ever)
    #

    startup.maybe_show_first_run_instructions(
        config,
        save_config
    )

    #
    # 4. Main window
    #

    window = MainWindow(config)

    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":

    try:

        main()

    except Exception:

        text = traceback.format_exc()

        _write_crash_log(text)

        try:

            app = QApplication.instance() or QApplication(sys.argv)

            box = QMessageBox()

            box.setWindowTitle("onscreenmenu - crashed")

            box.setText(
                "onscreenmenu hit an error and has to close.\n\n"
                "Details were saved to:\n"
                + _crash_log_path()
            )

            box.setDetailedText(text)

            box.exec()

        except Exception:

            pass

        raise
