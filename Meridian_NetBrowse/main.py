"""
Meridian NetBrowse Entry Point

A fork of CyberDeck Browser, kept in its own separate source tree
(Meridian_NetBrowse/) — not the same files, not imported by Meridian
Launcher. Differences from CyberDeck Browser:
  - No first-boot cyberpunk-effects prompt (removed outright).
  - No cyberpunk aesthetic GUI options in Settings (hud/CRT/scanlines/
    glitch checkboxes removed from ui/settings_dialog.py); those effects
    are forced off in config.py's DEFAULTS regardless.
  - Supports --box=X,Y,W,H, launched by Meridian Launcher's Browser
    section to size/position this window inside that section's
    list-frame box instead of covering the screen — never OS fullscreen.
"""


import sys


from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt



from config import load_config

from ui.main_window import MainWindow
from ui.loading_screen import LoadingScreen




def _handle_browser_registration_cli():
    """Let another app (Meridian Launcher's macro) register/unregister
    Meridian NetBrowse as the default browser by launching us with a flag,
    instead of duplicating the registry logic. Returns True if a flag was
    handled and the process should exit."""
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


def _parse_box_arg():
    """--box=X,Y,W,H — screen coordinates Meridian Launcher wants this
    window sized/positioned to (its Browser section's list-frame box).
    Returns (x, y, w, h) ints, or None if absent/malformed."""
    for arg in sys.argv[1:]:
        if arg.startswith("--box="):
            try:
                parts = [int(p) for p in arg[len("--box="):].split(",")]
                if len(parts) == 4:
                    return tuple(parts)
            except ValueError:
                pass
    return None


def main():
    if _handle_browser_registration_cli():
        return

    Qt.HighDpiScaleFactorRoundingPolicy.PassThrough

    app = QApplication(
        sys.argv
    )


    config = load_config()

    # Cyberpunk visual effects (HUD/CRT/scanlines/glitch) are permanently
    # off in Meridian NetBrowse — there is no prompt or Settings option to
    # turn them on, unlike CyberDeck Browser. Enforced here too (not just
    # in config.py's DEFAULTS) so an old config file copied over by hand
    # can't re-enable them.
    config["hud_enabled"] = False
    config["crt_enabled"] = False
    config["scanlines_enabled"] = False
    config["glitch_enabled"] = False

    box = _parse_box_arg()

    #
    # Meridian Launcher passes --window-mode=borderless-fullscreen when it
    # opens this app, asking for windowed (borderless) fullscreen for this
    # run regardless of whatever was last saved. This only affects the
    # in-memory config for this run - it is never written back to disk, so
    # a person's own saved preference (set from Meridian NetBrowse's own
    # settings) survives the next time they open it by hand. Ignored when
    # --box= is present — boxed mode always wins.
    #

    if "--window-mode=borderless-fullscreen" in sys.argv and not box:

        config["fullscreen"] = True


    #
    # A URL handed to us on the command line - how Windows invokes the
    # default browser ("...MeridianNetBrowse.exe" "%1"), how Meridian
    # Launcher's Browser section routes an internally-launched URL here,
    # and how other Meridian apps route a link here. The first argv entry
    # that looks like a URL wins; flags (starting with "-") are ignored.
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


    def _apply_geometry(widget):
        """Used for the loading screen only — MainWindow applies its own
        geometry internally (see ui/main_window.py), reading config["__box_geometry"]."""
        if box:
            x, y, w, h = box
            widget.move(x, y)
            widget.resize(max(200, w), max(150, h))
            widget.show()
        elif config.get("fullscreen", True):
            # Already frameless, so "fullscreen" just means covering the
            # primary screen exactly — not Qt's showFullScreen() state,
            # which behaves like a real fullscreen mode switch on some
            # platforms. Borderless windowed instead.
            screen_geo = QApplication.primaryScreen().geometry()
            widget.move(screen_geo.x(), screen_geo.y())
            widget.resize(screen_geo.width(), screen_geo.height())
            widget.show()
        else:
            widget.resize(600, 300)
            widget.show()


    def start_loading_screen():

        loading = LoadingScreen()

        _apply_geometry(loading)

        state["loading"] = loading

        loading.finished.connect(
            start_main_window
        )


    def start_main_window():

        window = MainWindow(
            config,
            startup_url,
            box
        )

        state["window"] = window

        state["loading"].close()


    # No first-boot cyberpunk-effects prompt in Meridian NetBrowse — go
    # straight to the loading screen every time.
    start_loading_screen()


    sys.exit(
        app.exec()
    )




if __name__ == "__main__":

    main()
