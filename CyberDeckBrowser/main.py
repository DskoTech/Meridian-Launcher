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




def _handle_browser_registration_cli():
    """Let another app (Meridian Launcher's macro) register/unregister
    CyberDeck as the default browser by launching us with a flag, instead
    of duplicating the registry logic. Returns True if a flag was handled
    and the process should exit."""
    if "--register-default-browser" in sys.argv or "--unregister-default-browser" in sys.argv:
        try:
            import default_browser
            exe = sys.executable
            if "--unregister-default-browser" in sys.argv:
                default_browser.unregister()
            else:
                default_browser.register(exe)
        except Exception:
            pass
        return True
    return False


def main():
    if _handle_browser_registration_cli():
        return

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
    # A URL handed to us on the command line - how Windows invokes the
    # default browser ("...CyberDeckBrowser.exe" "%1") and how other
    # Meridian apps route a link here. The first argv entry that looks
    # like a URL wins; flags (starting with "-") are ignored.
    #

    startup_url = None

    for arg in sys.argv[1:]:

        if arg.startswith("-"):

            continue

        low = arg.lower()

        if low.startswith(("http://", "https://", "file://", "ftp://")) or "." in arg:

            startup_url = arg

            break


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
            config,
            startup_url
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
