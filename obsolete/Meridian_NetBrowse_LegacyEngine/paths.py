"""
CyberDeck App Paths

Resolves the application's root folder correctly
whether running:

- from source (python main.py)
- as a PyInstaller-compiled executable

Using __file__ alone breaks once frozen, since it
then points somewhere inside PyInstaller's bundled
internals rather than the folder the .exe actually
lives in. Anything that needs to find files sitting
next to the app (osk.bat, config, bookmarks) should
import APP_ROOT from here instead of computing its
own relative path.
"""


import sys
import os




def get_app_root():

    if getattr(
        sys,
        "frozen",
        False
    ):

        #
        # Running as a compiled exe - use the
        # executable's own folder.
        #

        return os.path.dirname(
            sys.executable
        )

    #
    # Running from source - this file lives at the
    # project root alongside main.py.
    #

    return os.path.dirname(
        os.path.abspath(__file__)
    )




APP_ROOT = get_app_root()


#
# DATA_DIR holds CyberDeck Browser's own persistent data (its config and
# bookmarks) under %LOCALAPPDATA%\Meridian Launcher\CyberDeckBrowser\,
# rather than next to the exe - the app folder itself no longer needs to be
# writable (e.g. it can sit in Program Files).
#

def _get_data_dir():

    local_appdata = os.environ.get("LOCALAPPDATA") or os.path.join(
        os.path.expanduser("~"), "AppData", "Local"
    )

    # Meridian NetBrowse is a distinct fork of CyberDeck Browser (see
    # Meridian_NetBrowse/) — its own data directory so the two never read
    # or clobber each other's config/bookmarks.
    data_dir = os.path.join(local_appdata, "Meridian Launcher", "MeridianNetBrowse")

    os.makedirs(data_dir, exist_ok=True)

    return data_dir


DATA_DIR = _get_data_dir()


def _migrate_legacy_file(filename):
    """Carries a pre-update data file sitting next to the exe over to the
    new %LOCALAPPDATA% location, if the new location doesn't have one yet."""

    old_path = os.path.join(APP_ROOT, filename)

    new_path = os.path.join(DATA_DIR, filename)

    if os.path.exists(old_path) and not os.path.exists(new_path):

        try:
            import shutil
            shutil.copy2(old_path, new_path)
        except OSError:
            pass


for _f in ("cyberdeck_config.json", "cyberdeck_bookmarks.json"):
    _migrate_legacy_file(_f)
