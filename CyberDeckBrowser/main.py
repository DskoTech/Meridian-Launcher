"""
CyberDeck Browser Entry Point

Also serves as Meridian Launcher's boxed browser engine (the Browser
section, and webapp plugins like Telegram/Discord/etc): passing --box=
sizes/positions this window into a section's list-frame box instead of
covering the screen, and skips the cyberpunk first-boot prompt/effects
for that run (never written back to the saved config, so your own
cyberpunk preference for standalone use is untouched); --minimal-menu
additionally strips the Y/X menus down to "Exit Program" and hides the
tab bar. Standalone CyberDeckBrowser (no flags) behaves exactly as
before - full cyberpunk prompt/effects, full menus, tabs visible.

This used to be duplicated into a second app (Meridian NetBrowse) with
its own separate QtWebEngine bundle just to get boxed/minimal-menu
behavior - merged back in here instead, since running two full Chromium
engines side by side in one suite was the single biggest contributor to
its compiled size.
"""


import os
import sys

from crash_logger import install_crash_logging
install_crash_logging("CyberDeckBrowser")

try:
    import psutil
except ImportError:
    psutil = None


def _another_standalone_instance_running():
    """Only guards the STANDALONE launch path (no --box=) - CyberDeckBrowser
    is intentionally multi-instance when boxed by Meridian Launcher (the
    Browser section and each webapp plugin like Telegram/Discord get
    their own instance simultaneously), so this must never block that.
    Excludes both our own PID and our own PARENT's PID: a compiled
    --onefile build's bootloader briefly runs as its own process sharing
    the same exe name before exec'ing the real app as a child, so on
    every single compiled launch two "CyberDeckBrowser.exe" processes are
    alive for a moment - only excluding our own PID (not the parent's
    too) would make every launch falsely conclude "already running" and
    exit immediately (the exact bug found and fixed in onscreenmenu's own
    single-instance check)."""
    if psutil is None:
        return False
    my_pid = os.getpid()
    my_parent_pid = os.getppid()
    for proc in psutil.process_iter(["pid", "name"]):
        try:
            if proc.pid in (my_pid, my_parent_pid):
                continue
            if (proc.info.get("name") or "").lower() == "cyberdeckbrowser.exe":
                return True
        except (psutil.NoSuchProcess, psutil.AccessDenied, Exception):
            continue
    return False


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


def _parse_box_arg():
    """--box=X,Y,W,H — screen coordinates Meridian Launcher wants this
    window sized/positioned to (a section's list-frame box, or a webapp
    plugin's). Returns (x, y, w, h) ints, or None if absent/malformed."""
    for arg in sys.argv[1:]:
        if arg.startswith("--box="):
            try:
                parts = [int(p) for p in arg[len("--box="):].split(",")]
                if len(parts) == 4:
                    return tuple(parts)
            except ValueError:
                pass
    return None


def _parse_notify_exit_arg():
    """--notify-exit=<which> — an identifier ("explorer", "browser", or a
    plugin id) Meridian Launcher wants echoed back to its local
    /internal/plugin-exited endpoint the instant this window closes, so
    it can hand focus/controls back immediately instead of waiting for
    the whole process (including QtWebEngine/Chromium teardown, which can
    take a while) to actually exit."""
    for arg in sys.argv[1:]:
        if arg.startswith("--notify-exit="):
            return arg[len("--notify-exit="):]
    return None


def main():
    if _handle_browser_registration_cli():
        return

    Qt.HighDpiScaleFactorRoundingPolicy.PassThrough

    app = QApplication(
        sys.argv
    )


    config = load_config()

    box = _parse_box_arg()
    minimal_menu = "--minimal-menu" in sys.argv
    notify_which = _parse_notify_exit_arg()

    # Only guard the standalone path (no --box=) - boxed instances are
    # intentionally multi-instance (Browser section + each webapp plugin
    # get their own), and Meridian Launcher already manages not double-
    # loading those itself.
    if not box and _another_standalone_instance_running():
        return

    #
    # Meridian Launcher passes --window-mode=borderless-fullscreen when it
    # opens this app, asking for windowed (borderless) fullscreen for this
    # run regardless of whatever was last saved. This only affects the
    # in-memory config for this run - it is never written back to disk, so
    # a person's own saved preference (set from CyberDeck Browser's own
    # settings) survives the next time they open it by hand. Ignored when
    # --box= is present - boxed mode always wins.
    #

    if "--window-mode=borderless-fullscreen" in sys.argv and not box:

        config["fullscreen"] = True

    #
    # Boxed (always the case when Meridian Launcher opens this): cyberpunk
    # visual effects are forced off for this run, same as they always were
    # for the separate Meridian NetBrowse app - not saved back to disk.
    #

    if box:
        config["hud_enabled"] = False
        config["crt_enabled"] = False
        config["scanlines_enabled"] = False
        config["glitch_enabled"] = False


    #
    # A URL handed to us on the command line - how Windows invokes the
    # default browser ("...CyberDeckBrowser.exe" "%1"), how Meridian
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
        """Boxed mode (Meridian Launcher) always wins over fullscreen,
        which itself wins over a plain default-sized window."""
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
            box,
            minimal_menu,
            notify_which
        )

        state["window"] = window

        state["loading"].close()


    #
    # First boot: ask whether to enable the cyberpunk visual effects
    # before anything else appears - but never when boxed (Meridian
    # Launcher), where effects are already forced off above and there's
    # no standalone-app context for a first-boot prompt to make sense in.
    #

    if box:

        start_loading_screen()

    elif not config.get(

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
