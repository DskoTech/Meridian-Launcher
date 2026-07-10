"""
onscreenmenu Recent Apps Tracker (Select button)

Every 30 seconds, checks which window is currently in the
foreground. If it's a new window (and not onscreenmenu itself),
it's added to a rolling list of the last 6 distinct windows, with
the oldest entry dropped once the list exceeds 6.

This list backs the Select-button "switch to a recent program"
menu. It's local-only and visible to the person in that menu -
nothing is written anywhere else or sent off the machine.
"""

import os

from PySide6.QtCore import QObject, QTimer, Signal

import win32con
import win32gui
import win32process


MAX_RECENT = 6

POLL_INTERVAL_MS = 30_000


class RecentAppsTracker(QObject):

    updated = Signal(list)


    def __init__(
        self,
        interval_ms=POLL_INTERVAL_MS
    ):

        super().__init__()

        self.recent = []

        self.self_pid = os.getpid()

        self.timer = QTimer()

        self.timer.timeout.connect(
            self.poll
        )

        self.timer.start(interval_ms)


    def poll(self):

        try:

            hwnd = win32gui.GetForegroundWindow()

        except Exception:

            return

        if not hwnd:

            return

        try:

            _, pid = win32process.GetWindowThreadProcessId(hwnd)

        except Exception:

            return

        if pid == self.self_pid:

            #
            # onscreenmenu's own overlay/popups never get added
            # to its own recent-apps list.
            #

            return

        title = win32gui.GetWindowText(hwnd)

        if not title:

            return

        self.recent = [

            entry
            for entry in self.recent
            if entry["hwnd"] != hwnd

        ]

        self.recent.append(
            {
                "hwnd": hwnd,
                "pid": pid,
                "title": title
            }
        )

        if len(self.recent) > MAX_RECENT:

            self.recent = self.recent[-MAX_RECENT:]

        self.updated.emit(
            self.recent
        )


    def focus(
        self,
        hwnd
    ):

        if not win32gui.IsWindow(hwnd):

            return False

        try:

            win32gui.ShowWindow(
                hwnd,
                win32con.SW_RESTORE
            )

            win32gui.SetForegroundWindow(hwnd)

            return True

        except Exception:

            return False
