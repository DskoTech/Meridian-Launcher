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


import ctypes
import os
import sys

from crash_logger import install_crash_logging
install_crash_logging("CyberDeckBrowser")

try:
    import psutil
except ImportError:
    psutil = None


def _find_widevine_cdm():
    """Looks for widevinecdm.dll from an existing Chrome or Edge install
    on this machine. Returns its path, or None if neither is installed.

    WHY THIS IS NEEDED (streaming sites playing on YouTube but not
    Netflix/Tubi/Pluto/etc)
    -----------------------------------------------------------------
    Netflix always requires Widevine DRM to play anything at all; Tubi,
    Pluto, and most other ad-supported streamers require it for at
    least a meaningful chunk of their catalog too. YouTube mostly
    doesn't (most of its catalog streams unencrypted). Widevine's actual
    decryption module is a closed-source binary Google licenses to
    browser vendors - Qt/PySide6 has never been permitted to bundle it
    themselves, on Windows or anywhere else, so a stock QtWebEngine
    browser can play YouTube fine and simply has no way to decrypt a
    Widevine-protected stream at all until it's explicitly pointed at a
    real CDM binary from somewhere.

    Chrome and Edge both download their own copy of it (as a browser
    component, auto-updated) the moment either is installed and run at
    least once - this just locates whichever one exists and hands its
    path to Chromium via the --widevine-path switch below. If NEITHER
    Chrome nor Edge has ever actually been run on this machine (just
    installed isn't enough - the component downloads on first launch),
    this returns None and DRM playback stays unavailable; there's no way
    to conjure the binary from nothing since Meridian can't legally
    redistribute it itself.

    Doesn't touch proprietary codec support (H.264/AAC) - that's a
    separate, compile-time Qt build option this can't affect at
    runtime. Most Widevine-protected streams also offer a VP9 (royalty-
    free, not patent-encumbered) variant for exactly this reason, so
    this alone is often still enough even without H.264 - but if a
    specific title only offers H.264 renditions, no runtime flag fixes
    that; only a PySide6/Qt build compiled with proprietary codec
    support would."""
    if sys.platform != "win32":
        return None
    roots = []
    localappdata = os.environ.get("LOCALAPPDATA")
    if localappdata:
        roots.append(os.path.join(localappdata, "Google", "Chrome", "User Data", "WidevineCdm"))
        roots.append(os.path.join(localappdata, "Microsoft", "Edge", "User Data", "WidevineCdm"))
    programfiles = os.environ.get("PROGRAMFILES", r"C:\Program Files")
    programfiles_x86 = os.environ.get("PROGRAMFILES(X86)", r"C:\Program Files (x86)")
    for base in (programfiles, programfiles_x86):
        roots.append(os.path.join(base, "Google", "Chrome", "Application", "WidevineCdm"))
        roots.append(os.path.join(base, "Microsoft", "Edge", "Application", "WidevineCdm"))

    for root in roots:
        if not os.path.isdir(root):
            continue
        # Versioned subfolder (e.g. "4.10.2732.0") - take the newest if
        # more than one is present (old versions don't always get cleaned up).
        try:
            versions = sorted(
                (d for d in os.listdir(root) if os.path.isdir(os.path.join(root, d))),
                reverse=True,
            )
        except OSError:
            continue
        for version in versions:
            candidate = os.path.join(root, version, "_platform_specific", "win_x64", "widevinecdm.dll")
            if os.path.isfile(candidate):
                return candidate
    return None


def _to_short_path(path):
    """8.3 short path (e.g. C:\\PROGRA~1\\...) - guaranteed no spaces,
    used so a real Windows path can go into QTWEBENGINE_CHROMIUM_FLAGS
    safely. That env var is split on whitespace without reliably
    respecting quotes across Qt/QtWebEngine versions - wrapping a
    space-containing value in literal double-quotes (what this code
    used to do) is exactly the kind of thing that LOOKS like it should
    work and doesn't: "C:\\Program Files\\Google\\Chrome\\User Data\\..."
    (both "Program Files" and "User Data" contain spaces) would get
    split into multiple garbled tokens, handing Chromium a malformed
    command line - not a crash, just pages silently never loading,
    which is a much harder failure mode to trace back to its cause.
    Falls back to the original path unchanged if short-path generation
    fails (some systems disable 8.3 name generation via policy) - on
    those systems a CDM path really will still hit this problem."""
    try:
        buf = ctypes.create_unicode_buffer(260)
        n = ctypes.windll.kernel32.GetShortPathNameW(path, buf, 260)
        if n and n <= 260:
            return buf.value
    except Exception:
        pass
    return path


def _configure_streaming_playback():
    """Sets QTWEBENGINE_CHROMIUM_FLAGS before any PySide6/QtWebEngine
    import happens - Chromium reads this environment variable during its
    own static initialization when the QtWebEngine module first loads,
    not at QApplication() construction time, so this MUST run before
    that import, not just before main() does its own setup. See
    _find_widevine_cdm's docstring for why the Widevine part exists.

    Every flag added here can be independently disabled via an
    environment variable for testing/bisection - set it to anything
    non-empty before launching CyberDeckBrowser.exe (from a terminal, so
    the variable is actually inherited: `set MERIDIAN_DISABLE_WIDEVINE_
    FLAGS=1 && CyberDeckBrowser.exe`) to rule a specific one in or out:
      MERIDIAN_DISABLE_WIDEVINE_FLAGS   - skip --widevine-path/--ppapi-widevine-path
      MERIDIAN_DISABLE_AUTOPLAY_FLAG    - skip --autoplay-policy

    Two more flags beyond Widevine, for the same "plays on YouTube but
    not Tubi/Pluto/etc" class of problem:
      - --ppapi-widevine-path alongside --widevine-path: some
        QtWebEngine/Chromium versions still expect the older PPAPI-
        plugin-based path instead of the newer component-based one;
        setting both costs nothing since Chromium ignores switches it
        doesn't recognize.
      - --autoplay-policy=no-user-gesture-required: a genuinely
        different failure mode than DRM that looks identical from the
        outside ("page loads, nothing plays, no error"). Chromium
        blocks a <video> from starting without a real user gesture on
        it specifically, and several streaming players' own JS silently
        stalls waiting for a canplay/playing event that never fires,
        rather than showing a click-to-play prompt."""
    existing = os.environ.get("QTWEBENGINE_CHROMIUM_FLAGS", "")
    flags_to_add = []

    if not os.environ.get("MERIDIAN_DISABLE_WIDEVINE_FLAGS"):
        cdm_path = _find_widevine_cdm()
        if cdm_path:
            cdm_path = _to_short_path(cdm_path)
            if "--widevine-path" not in existing:
                flags_to_add.append(f"--widevine-path={cdm_path}")
            if "--ppapi-widevine-path" not in existing:
                flags_to_add.append(f"--ppapi-widevine-path={cdm_path}")

    if not os.environ.get("MERIDIAN_DISABLE_AUTOPLAY_FLAG"):
        if "--autoplay-policy" not in existing:
            flags_to_add.append("--autoplay-policy=no-user-gesture-required")

    if flags_to_add:
        os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = (existing + " " + " ".join(flags_to_add)).strip()


_configure_streaming_playback()


def _configure_persistent_web_profile(profile_key=None):
    """Configures QWebEngineProfile.defaultProfile() - called from
    main() once box/notify_which are known, before any browser view/page
    can grab the profile unconfigured.

    PERSISTENT LOGINS - the actual root cause of "forgets I logged in
    when I close the window and resume": defaultProfile() was never
    given an organization/app name, an explicit persistent storage
    path, or a cookie policy. Either gap alone causes it: (1) without a
    stable app/org name, Qt's auto-derived storage location isn't
    guaranteed stable across runs; (2) without ForcePersistentCookies,
    Qt respects a site's own "forget this when the browser closes" flag
    on session cookies - which is exactly what most login systems set,
    and is normally masked by how desktop Chrome treats "closing the
    window" differently from "ending the session." Fixed by setting
    both explicitly, at a real path under the suite's shared data
    folder, configured before any browser view exists so nothing can
    grab the profile unconfigured.

    PER-CONTEXT ISOLATION (profile_key) - CyberDeckBrowser is
    deliberately multi-instance when boxed (see _another_standalone_
    instance_running's docstring: the Browser section and each webapp
    plugin get their own simultaneously-running process). A single
    shared persistent storage path across ALL of them looked fine in
    isolation but broke the moment two were open at once: Chromium's
    profile storage uses its own singleton lock to stop two unrelated
    OS processes from touching the same profile directory concurrently
    (the same reason launching real Chrome twice against the same
    --user-data-dir warns instead of just working) - the SECOND process
    to grab a shared profile would have its Chromium renderer silently
    fail to come up at all, while the surrounding Qt window chrome
    (background, exit button) rendered fine regardless, since that part
    is plain Qt with no dependency on Chromium succeeding.
    profile_key (notify_which - "browser", a plugin id, or None for a
    standalone launch) gives each *kind* of window its own storage
    subfolder instead: stable and shared across repeat opens of the
    same context (so Browser-section logins still persist run to run),
    isolated from whatever else happens to be open at the same time.
    This also means a plugin webapp's login (Telegram, say) no longer
    leaks into the general Browser section's cookie jar or vice versa,
    which is arguably more correct than one shared jar would have been
    anyway.

    USER-AGENT - QtWebEngine's default UA includes a "QtWebEngine/x.x"
    component real Chrome never sends; several streaming sites allow-
    list known UA strings rather than testing capability directly.

    PLUGINS - Chromium's EME/Widevine implementation is architecturally
    still a "plugin" internally, and QtWebEngine doesn't default this
    the way real desktop Chrome does, so even a correctly-provided CDM
    path (see _configure_streaming_playback above) can go unused
    without it.

    Each piece below can be independently disabled via an environment
    variable for testing/bisection, same convention as
    _configure_streaming_playback's flags - see that function's
    docstring for how to actually set one before launching:
      MERIDIAN_DISABLE_PROFILE_PERSISTENCE - skip org/app name, storage
        path, cache path, and cookie policy entirely (falls back to
        whatever QtWebEngine's own defaults would have been)
      MERIDIAN_DISABLE_UA_OVERRIDE         - skip the custom User-Agent
      MERIDIAN_DISABLE_PLUGINS_FLAGS       - skip PluginsEnabled/
        PlaybackRequiresUserGesture/FullScreenSupportEnabled"""
    from PySide6.QtCore import QCoreApplication
    from PySide6.QtWebEngineCore import QWebEngineProfile

    profile = QWebEngineProfile.defaultProfile()

    if not os.environ.get("MERIDIAN_DISABLE_PROFILE_PERSISTENCE"):
        QCoreApplication.setOrganizationName("DskoTech")
        QCoreApplication.setApplicationName("CyberDeckBrowser")

        # Sanitize to a plain folder-name-safe string - profile_key can be
        # a plugin id, which is developer-chosen but never validated as a
        # safe path component.
        safe_key = "".join(c if (c.isalnum() or c in "-_") else "_" for c in (profile_key or "standalone"))
        storage_path = os.path.join(
            os.environ.get("LOCALAPPDATA", os.path.expanduser("~")),
            "Meridian Launcher", "CyberDeckBrowser", "WebProfile", safe_key,
        )
        os.makedirs(storage_path, exist_ok=True)
        profile.setPersistentStoragePath(storage_path)
        profile.setCachePath(os.path.join(storage_path, "Cache"))
        profile.setPersistentCookiesPolicy(profile.PersistentCookiesPolicy.ForcePersistentCookies)

    if not os.environ.get("MERIDIAN_DISABLE_UA_OVERRIDE"):
        profile.setHttpUserAgent(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )

    if not os.environ.get("MERIDIAN_DISABLE_PLUGINS_FLAGS"):
        settings = profile.settings()
        settings.setAttribute(settings.WebAttribute.PluginsEnabled, True)
        settings.setAttribute(settings.WebAttribute.PlaybackRequiresUserGesture, False)
        settings.setAttribute(settings.WebAttribute.JavascriptEnabled, True)
        settings.setAttribute(settings.WebAttribute.FullScreenSupportEnabled, True)
        settings.setAttribute(settings.WebAttribute.LocalStorageEnabled, True)


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

    _configure_persistent_web_profile(notify_which)

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
