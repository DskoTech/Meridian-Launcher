"""
onscreenmenu Entry Point
"""

import os
import sys
import traceback

from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtCore import Qt

from config import load_config, save_config, _config_dir

from features import startup

from ui.main_window import MainWindow


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
