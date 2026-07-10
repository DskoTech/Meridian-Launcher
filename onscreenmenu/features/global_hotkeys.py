"""
onscreenmenu Global Hotkeys

Ctrl+H - hibernate / resume (same action as pressing Start+Select
          together on the controller)
Ctrl+T - close onscreenmenu

These work system-wide (not just while onscreenmenu has focus),
matching the app's "controller substitute" purpose - the physical
keyboard shortcuts are documented up front in the first-run
instructions.

Runs on the `keyboard` package's own OS-level hook thread. Signals
are used to safely hand control back to the Qt main thread.
"""

from PySide6.QtCore import QObject, Signal

import keyboard


class GlobalHotkeys(QObject):

    hibernate_toggle_requested = Signal()

    quit_requested = Signal()


    def __init__(self):

        super().__init__()

        self._registered = False

        try:

            keyboard.add_hotkey(
                "ctrl+h",
                self._on_hibernate
            )

            keyboard.add_hotkey(
                "ctrl+t",
                self._on_quit
            )

            self._registered = True

        except Exception:

            #
            # If the hook can't be installed (e.g. missing
            # privileges), onscreenmenu still works fully via
            # the controller - these are a convenience layer.
            #

            self._registered = False


    def _on_hibernate(self):

        self.hibernate_toggle_requested.emit()


    def _on_quit(self):

        self.quit_requested.emit()


    def stop(self):

        if not self._registered:

            return

        try:

            keyboard.remove_hotkey(
                "ctrl+h"
            )

            keyboard.remove_hotkey(
                "ctrl+t"
            )

        except Exception:

            pass
