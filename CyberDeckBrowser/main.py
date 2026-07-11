"""
CyberDeck Browser Entry Point
"""


import sys


from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt



from config import load_config, save_config

from ui.main_window import MainWindow
from ui.loading_screen import LoadingScreen
from ui.cyberpunk_prompt import CyberpunkPrompt




def main():
    Qt.HighDpiScaleFactorRoundingPolicy.PassThrough

    app = QApplication(
        sys.argv
    )


    config = load_config()

    #
    # Meridian Launcher passes --window-mode=borderless-fullscreen when it
    # opens this app, asking for windowed (borderless) fullscreen for this
    # run regardless of whatever was last saved. This only affects the
    # in-memory config for this run - it is never written back to disk, so
    # a person's own saved preference (set from CyberDeck Browser's own
    # settings) survives the next time they open it by hand.
    #

    if "--window-mode=borderless-fullscreen" in sys.argv:

        config["fullscreen"] = True


    #
    # Keeps references alive once created inside
    # the closures below (otherwise Python would
    # garbage-collect them).
    #

    state = {}


    def start_loading_screen():

        loading = LoadingScreen()

        if config.get("fullscreen", True):

            # Already frameless, so "fullscreen" just means covering the
            # primary screen exactly — not Qt's showFullScreen() state,
            # which behaves like a real fullscreen mode switch on some
            # platforms. Borderless windowed instead.
            screen_geo = QApplication.primaryScreen().geometry()

            loading.move(screen_geo.x(), screen_geo.y())

            loading.resize(screen_geo.width(), screen_geo.height())

            loading.show()

        else:

            loading.resize(600, 300)

            loading.show()

        state["loading"] = loading

        loading.finished.connect(
            start_main_window
        )


    def start_main_window():

        window = MainWindow(
            config
        )

        state["window"] = window

        window.show()

        state["loading"].close()


    #
    # First boot: ask whether to enable the
    # cyberpunk visual effects before anything
    # else appears.
    #

    if not config.get(

        "cyberpunk_prompt_shown",

        False

    ):

        def handle_prompt_answer(
            enabled
        ):

            config["hud_enabled"] = enabled

            config["crt_enabled"] = enabled

            config["scanlines_enabled"] = enabled

            config["glitch_enabled"] = enabled

            config["cyberpunk_prompt_shown"] = True

            save_config(
                config
            )

            start_loading_screen()


        prompt = CyberpunkPrompt()

        if config.get("fullscreen", True):

            screen_geo = QApplication.primaryScreen().geometry()

            prompt.move(screen_geo.x(), screen_geo.y())

            prompt.resize(screen_geo.width(), screen_geo.height())

            prompt.show()

        else:

            prompt.resize(600, 260)

            prompt.show()

        state["prompt"] = prompt

        prompt.answered.connect(
            handle_prompt_answer
        )

    else:

        start_loading_screen()


    sys.exit(
        app.exec()
    )




if __name__ == "__main__":

    main()
