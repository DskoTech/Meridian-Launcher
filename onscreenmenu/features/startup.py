"""
onscreenmenu Startup Flow

Handles, in order:

1. "Wrong place" install prompt
   If running as a built exe and it is NOT sitting in
   C:\\Program Files\\DskoTech, ask the person (Yes/No) whether
   to copy itself there. A "No" is remembered so we don't nag
   on every single launch.

2. Splash screen
   Quick branded splash shown while the rest of the app spins up.

3. First-run instructions
   Shown once, ever (tracked in config), explaining what
   onscreenmenu is and how to control it.
"""

import os
import sys
import shutil

from PySide6.QtWidgets import QMessageBox, QSplashScreen
from PySide6.QtGui import QPixmap, QPainter, QColor, QFont
from PySide6.QtCore import Qt, QTimer


INSTALL_DIR = r"C:\Program Files\DskoTech"
EXE_NAME = "onscreenmenu.exe"


FIRST_RUN_TEXT = (
    "onscreenmenu is a videogame controller based substitute for "
    "mouse mode and virtual keyboard that allows for custom menus "
    "that one might need to substitute for a lack of a dedicated "
    "functional Xbox pause screen and native controller support "
    "when running Windows in Xbox mode.\n\n"
    "You can jump to recent programs with ease, and open your "
    "favorite programs or files, or program useful keyboard combos "
    "for use without a keyboard.\n\n"
    "Controls:\n"
    "  A - Left click\n"
    "  B - Right click\n"
    "  X - Custom key combo menu (also has Virtual Keyboard and Close "
    "Onscreenmenu)\n"
    "  Y - Custom shortcut menu (also has Controls, to show this again)\n"
    "  Select - Switch to a recently used program\n"
    "  R3 (click right stick) - Hibernate (or wake) onscreenmenu, "
    "so you can game or use the computer without it. Press it "
    "again to go back to using it.\n\n"
    "Keyboard shortcuts (from a physical keyboard):\n"
    "  Ctrl + H - Hibernate / resume onscreenmenu\n"
    "  Ctrl + T - Close onscreenmenu"
)


#
# ---- self-install prompt ----
#

def is_frozen():

    return getattr(
        sys,
        "frozen",
        False
    )


def current_exe_path():

    if is_frozen():

        return os.path.abspath(sys.executable)

    return os.path.abspath(sys.argv[0])


def is_already_installed():

    return (

        os.path.normcase(
            os.path.dirname(
                current_exe_path()
            )
        )

        ==

        os.path.normcase(
            INSTALL_DIR
        )

    )


def maybe_prompt_install(config, save_config_fn):

    """
    Only meaningful for a built/frozen exe. When run from source
    (python main.py) this silently does nothing, since there is
    no single exe file to relocate.
    """

    if not is_frozen():

        return

    if is_already_installed():

        return

    if config.get(
        "skip_install_prompt",
        False
    ):

        return

    box = QMessageBox()

    box.setWindowTitle(
        "onscreenmenu"
    )

    box.setText(
        "onscreenmenu.exe is in the wrong place, do you want to fix this?"
    )

    box.setStandardButtons(
        QMessageBox.Yes | QMessageBox.No
    )

    choice = box.exec()

    if choice != QMessageBox.Yes:

        config["skip_install_prompt"] = True

        save_config_fn(config)

        return

    try:

        os.makedirs(
            INSTALL_DIR,
            exist_ok=True
        )

        destination = os.path.join(
            INSTALL_DIR,
            EXE_NAME
        )

        shutil.copy2(
            current_exe_path(),
            destination
        )

        QMessageBox.information(
            None,
            "onscreenmenu",
            "Copied to " + destination +
            "\n\nYou can launch it from there next time."
        )

    except Exception as error:

        QMessageBox.warning(
            None,
            "onscreenmenu",
            "Couldn't copy itself automatically (try running as "
            "administrator once):\n" + str(error)
        )


#
# ---- splash screen ----
#

def show_splash(app, duration_ms=1400):

    pixmap = QPixmap(
        520,
        260
    )

    pixmap.fill(
        QColor(
            16,
            16,
            32
        )
    )

    painter = QPainter(
        pixmap
    )

    painter.setPen(
        QColor(
            0,
            255,
            255
        )
    )

    title_font = QFont(
        "Consolas",
        28,
        QFont.Bold
    )

    painter.setFont(
        title_font
    )

    painter.drawText(
        pixmap.rect(),
        Qt.AlignCenter,
        "onscreenmenu"
    )

    subtitle_font = QFont(
        "Consolas",
        11
    )

    painter.setFont(
        subtitle_font
    )

    painter.setPen(
        QColor(
            160,
            220,
            230
        )
    )

    painter.drawText(
        0,
        pixmap.height() - 40,
        pixmap.width(),
        30,
        Qt.AlignCenter,
        "controller mouse & keyboard substitute"
    )

    painter.end()

    splash = QSplashScreen(
        pixmap
    )

    splash.setWindowFlag(
        Qt.WindowStaysOnTopHint
    )

    splash.show()

    app.processEvents()

    QTimer.singleShot(
        duration_ms,
        splash.close
    )

    return splash


#
# ---- first-run instructions ----
#

def maybe_show_first_run_instructions(config, save_config_fn):

    if config.get(
        "first_run_done",
        False
    ):

        return

    box = QMessageBox()

    box.setWindowTitle(
        "Welcome to onscreenmenu"
    )

    box.setTextFormat(
        Qt.PlainText
    )

    box.setText(
        FIRST_RUN_TEXT
    )

    box.setStandardButtons(
        QMessageBox.Ok
    )

    box.exec()

    config["first_run_done"] = True

    save_config_fn(config)
