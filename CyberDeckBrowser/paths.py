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
