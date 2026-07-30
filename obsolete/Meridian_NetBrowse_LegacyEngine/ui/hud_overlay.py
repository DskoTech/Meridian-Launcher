"""
CyberDeck HUD Overlay

A fullscreen, click-through, always-on-top decorative
layer, independent from browser functionality.

Renders:
- Top status bar (app name, network, clock)
- Corner HUD brackets
- System info panel (CPU/RAM/NET/CTRL/MODE)
- Controller input feedback (transient)
- CRT scanline effect (optional)
- Glitch flash transitions (optional, triggered
  externally on menu open / tab switch / etc)

Never intercepts mouse or keyboard input - it only
paints on top of everything else.
"""


import time

import psutil

from PySide6.QtWidgets import QWidget

from PySide6.QtGui import (
    QPainter,
    QColor,
    QPen,
    QFont,
    QGuiApplication
)

from PySide6.QtCore import Qt, QTimer

from ui.click_through import make_click_through




#
# Default cyberpunk palette
#

COLOR_BG = QColor(5, 8, 16, 170)
COLOR_PRIMARY = QColor(0, 255, 255)
COLOR_SECONDARY = QColor(176, 0, 255)
COLOR_WARNING = QColor(255, 85, 0)
COLOR_SUCCESS = QColor(40, 220, 110)




class HUDOverlay(QWidget):


    def __init__(
        self,
        config,
        parent=None
    ):

        super().__init__(parent)


        self.settings = {

            "hud_enabled": config.get(
                "hud_enabled", True
            ),

            "crt_enabled": config.get(
                "crt_enabled", True
            ),

            "scanlines_enabled": config.get(
                "scanlines_enabled", True
            ),

            "glitch_enabled": config.get(
                "glitch_enabled", True
            ),

            "animation_level": config.get(
                "animation_level", "MEDIUM"
            )

        }


        self.setWindowFlags(

            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint |
            Qt.Tool |
            Qt.WindowDoesNotAcceptFocus

        )

        self.setAttribute(
            Qt.WA_TransparentForMouseEvents
        )

        self.setAttribute(
            Qt.WA_TranslucentBackground
        )

        self.setAttribute(
            Qt.WA_NoSystemBackground
        )

        self.setFocusPolicy(
            Qt.NoFocus
        )


        #
        # State
        #

        self.session_start = time.time()

        self.cpu_percent = 0.0

        self.ram_percent = 0.0

        self.net_online = True

        self.controller_connected = False

        self.mode_text = "MOUSE + KEYBOARD"

        self.feedback_text = ""

        self.feedback_alpha = 0.0

        self.scan_offset = 0

        self.glitch_alpha = 0.0


        self.update_screen_geometry()


        #
        # Stats refresh (clock, CPU/RAM/net) - cheap,
        # always runs regardless of animation settings
        #

        self.stats_timer = QTimer()

        self.stats_timer.timeout.connect(
            self._refresh_stats
        )

        self.stats_timer.start(
            1000
        )

        self._refresh_stats()


        #
        # Animation loop - scanline flicker, glitch
        # decay, feedback fade. Only runs when at
        # least one animated effect is enabled.
        #

        self.anim_timer = QTimer()

        self.anim_timer.timeout.connect(
            self._advance_animation
        )

        self._sync_animation_timer()


        self.make_click_through()



    #
    # ---- setup ----
    #

    def update_screen_geometry(self):

        screen = QGuiApplication.primaryScreen()

        if not screen:

            return

        self.setGeometry(
            screen.virtualGeometry()
        )



    def make_click_through(self):

        make_click_through(self)



    #
    # ---- settings ----
    #

    def apply_settings(
        self,
        **kwargs
    ):

        self.settings.update(kwargs)

        self._sync_animation_timer()

        self.update()



    def _sync_animation_timer(self):

        animated = (

            self.settings["crt_enabled"]

            or

            self.settings["scanlines_enabled"]

            or

            self.settings["glitch_enabled"]

        ) and self.settings["animation_level"] != "LOW"

        if animated and not self.anim_timer.isActive():

            self.anim_timer.start(33)

        elif not animated and self.anim_timer.isActive():

            self.anim_timer.stop()



    #
    # ---- live updates from the app ----
    #

    def set_mode(
        self,
        text
    ):

        if text != self.mode_text:

            self.mode_text = text

            self.update()



    def set_controller_connected(
        self,
        connected
    ):

        if connected != self.controller_connected:

            self.controller_connected = connected

            self.update()



    def show_feedback(
        self,
        text
    ):

        if not self.settings["hud_enabled"]:

            return

        self.feedback_text = text

        self.feedback_alpha = 1.0

        self.update()



    def trigger_glitch(self):

        if not self.settings["glitch_enabled"]:

            return

        self.glitch_alpha = 1.0



    #
    # ---- background refresh ----
    #

    def _refresh_stats(self):

        try:

            self.cpu_percent = psutil.cpu_percent(
                interval=None
            )

            self.ram_percent = psutil.virtual_memory().percent

        except Exception:

            pass


        try:

            stats = psutil.net_if_stats()

            self.net_online = any(

                s.isup

                for name, s in stats.items()

                if name.lower() != "loopback"

            )

        except Exception:

            self.net_online = True


        self.update()



    def _advance_animation(self):

        self.scan_offset = (

            self.scan_offset + 1

        ) % 6


        if self.glitch_alpha > 0:

            self.glitch_alpha = max(

                0.0,

                self.glitch_alpha - 0.12

            )


        if self.feedback_alpha > 0:

            self.feedback_alpha = max(

                0.0,

                self.feedback_alpha - 0.03

            )


        self.update()



    #
    # ---- painting ----
    #

    def paintEvent(
        self,
        event
    ):

        painter = QPainter(self)

        painter.setRenderHint(
            QPainter.Antialiasing
        )


        if self.settings["hud_enabled"]:

            self._draw_corners(painter)

            self._draw_top_bar(painter)

            self._draw_feedback(painter)


        if (

            self.settings["crt_enabled"]

            or

            self.settings["scanlines_enabled"]

        ):

            self._draw_scanlines(painter)


        if self.glitch_alpha > 0:

            self._draw_glitch(painter)


        painter.end()



    def _mono_font(
        self,
        size,
        bold=False
    ):

        font = QFont(
            "Consolas"
        )

        font.setStyleHint(
            QFont.Monospace
        )

        font.setPointSize(
            size
        )

        font.setBold(
            bold
        )

        return font



    def _draw_top_bar(
        self,
        painter
    ):

        width = self.width()

        bar_height = 34


        painter.fillRect(

            0,
            0,
            width,
            bar_height,

            COLOR_BG

        )

        painter.setPen(
            QPen(
                COLOR_PRIMARY,
                1
            )
        )

        painter.drawLine(
            0,
            bar_height,
            width,
            bar_height
        )


        painter.setFont(
            self._mono_font(11, bold=True)
        )

        painter.setPen(
            COLOR_PRIMARY
        )

        painter.drawText(

            16,
            0,
            400,
            bar_height,

            Qt.AlignVCenter,

            "CYBERDECKBROWSER ONLINE"

        )


        clock_text = time.strftime(
            "%H:%M:%S"
        )

        net_color = (

            COLOR_SUCCESS

            if self.net_online

            else COLOR_WARNING

        )

        net_text = (

            "NETWORK: CONNECTED"

            if self.net_online

            else "NETWORK: OFFLINE"

        )


        painter.setFont(
            self._mono_font(10)
        )

        painter.setPen(
            net_color
        )

        painter.drawText(

            width - 320,
            0,
            180,
            bar_height,

            Qt.AlignVCenter,

            net_text

        )

        painter.setPen(
            COLOR_PRIMARY
        )

        painter.drawText(

            width - 120,
            0,
            100,
            bar_height,

            Qt.AlignVCenter | Qt.AlignRight,

            clock_text

        )



    def _draw_corners(
        self,
        painter
    ):

        painter.setPen(
            QPen(
                COLOR_PRIMARY,
                2
            )
        )

        length = 26

        margin = 6

        width = self.width()

        height = self.height()


        corners = [

            (margin, margin, 1, 1),

            (width - margin, margin, -1, 1),

            (margin, height - margin, 1, -1),

            (width - margin, height - margin, -1, -1)

        ]

        for x, y, dx, dy in corners:

            painter.drawLine(

                x,
                y,

                x + length * dx,
                y

            )

            painter.drawLine(

                x,
                y,

                x,
                y + length * dy

            )



    def _draw_feedback(
        self,
        painter
    ):

        if not self.feedback_text or self.feedback_alpha <= 0:

            return


        color = QColor(
            COLOR_PRIMARY
        )

        color.setAlphaF(
            self.feedback_alpha
        )

        painter.setFont(
            self._mono_font(12, bold=True)
        )

        painter.setPen(
            color
        )

        width = self.width()

        height = self.height()

        painter.drawText(

            0,
            height - 90,
            width,
            30,

            Qt.AlignHCenter,

            self.feedback_text

        )



    def _draw_scanlines(
        self,
        painter
    ):

        width = self.width()

        height = self.height()

        alpha = 18 if self.settings["animation_level"] == "LOW" else 24

        pen = QPen(
            QColor(0, 0, 0, alpha)
        )

        painter.setPen(
            pen
        )

        start = self.scan_offset if self.anim_timer.isActive() else 0

        y = start

        while y < height:

            painter.drawLine(
                0,
                y,
                width,
                y
            )

            y += 3



    def _draw_glitch(
        self,
        painter
    ):

        width = self.width()

        band_height = 6

        y = int(

            (1.0 - self.glitch_alpha)

            *

            self.height()

        )


        cyan = QColor(
            0,
            255,
            255,
            int(120 * self.glitch_alpha)
        )

        magenta = QColor(
            255,
            0,
            170,
            int(120 * self.glitch_alpha)
        )


        painter.fillRect(

            -4,
            y,
            width,
            band_height,

            cyan

        )

        painter.fillRect(

            4,
            y + band_height,
            width,
            band_height,

            magenta

        )
