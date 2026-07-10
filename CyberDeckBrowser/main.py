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
    # Keeps references alive once created inside
    # the closures below (otherwise Python would
    # garbage-collect them).
    #

    state = {}


    def start_loading_screen():

        loading = LoadingScreen()

        if config.get("fullscreen", True):

            loading.showFullScreen()

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

            prompt.showFullScreen()

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
