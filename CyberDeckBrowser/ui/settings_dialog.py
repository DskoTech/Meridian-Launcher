"""
CyberDeck Settings Dialog

Lets the person tune controller behavior and
cyberpunk visual effects:

- Mouse sensitivity
- Trigger boost multiplier
- Stick deadzone
- HUD / CRT / Scanlines / Glitch toggles
- Animation level

Opened from the Browser (Y) menu's "Settings" option.
"""


from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QDoubleSpinBox,
    QCheckBox,
    QComboBox,
    QPushButton
)

from PySide6.QtCore import Qt, Signal




class SettingsDialog(QWidget):


    #
    # Emitted with (sensitivity, trigger_boost, deadzone)
    #

    settings_changed = Signal(
        float,
        float,
        float
    )


    #
    # Emitted with a dict of visual effect settings:
    # hud_enabled, crt_enabled, scanlines_enabled,
    # glitch_enabled, animation_level
    #

    visual_settings_changed = Signal(
        dict
    )



    def __init__(
        self,
        config,
        parent=None
    ):

        super().__init__(parent)

        self.config = config

        self.setWindowFlags(

            Qt.FramelessWindowHint |
            Qt.Tool

        )

        self.resize(
            480,
            740
        )


        layout = QVBoxLayout(self)


        layout.addWidget(
            QLabel("SETTINGS")
        )


        #
        # Controller controls quick reference - what every
        # button and combo does, kept at the very top so
        # it's the first thing the settings window shows.
        #

        controls_label = QLabel(
            "<b>CONTROLLER CONTROLS</b><br>"
            "<table cellspacing='0' cellpadding='2'>"
            "<tr><td><b>Left stick</b></td><td>Move the cursor</td></tr>"
            "<tr><td><b>LT / RT (hold)</b></td><td>Cursor speed boost while held</td></tr>"
            "<tr><td><b>L3 (click left stick)</b></td><td>Reset page zoom</td></tr>"
            "<tr><td><b>Right stick up/down</b></td><td>Scroll the page</td></tr>"
            "<tr><td><b>Right stick left/right</b></td><td>Zoom out / in</td></tr>"
            "<tr><td><b>A</b></td><td>Left click / select (keyboard key, menu item)</td></tr>"
            "<tr><td><b>B</b></td><td>Right click; closes menus and the virtual keyboard</td></tr>"
            "<tr><td><b>D-pad</b></td><td>Navigate the virtual keyboard and popup menus; "
            "on a page: up/down scroll, left/right send arrow keys</td></tr>"
            "<tr><td><b>LB / RB</b></td><td>Previous / next browser tab</td></tr>"
            "<tr><td><b>Y</b></td><td>Browser menu (History, Downloads, Bookmarks, "
            "Translate, Settings, Find In Page)</td></tr>"
            "<tr><td><b>X</b></td><td>Tools menu</td></tr>"
            "<tr><td><b>Start</b></td><td>Open the search window</td></tr>"
            "<tr><td><b>Select / Back</b></td><td>Launch the Windows on-screen keyboard (osk.bat)</td></tr>"
            "</table>"
        )

        controls_label.setWordWrap(True)

        controls_label.setStyleSheet(
            "font-size:12px; color:#9fe8ff; border:1px solid #00ffff;"
            "border-radius:4px; padding:8px; background:#0c0c1c;"
        )

        layout.addWidget(
            controls_label
        )


        self.sensitivity_box = self._build_spin_row(

            layout,

            "Mouse Sensitivity",

            1.0,

            50.0,

            config.get("mouse_sensitivity", 30.0)

        )


        self.trigger_box = self._build_spin_row(

            layout,

            "Trigger Boost Multiplier",

            1.0,

            10.0,

            config.get("trigger_boost", 4.0)

        )


        self.deadzone_box = self._build_spin_row(

            layout,

            "Stick Deadzone",

            0.0,

            0.9,

            config.get("deadzone", 0.15)

        )


        layout.addWidget(
            QLabel("CYBERPUNK EFFECTS")
        )


        self.hud_check = self._build_check_row(

            layout,

            "HUD",

            config.get("hud_enabled", True)

        )


        self.crt_check = self._build_check_row(

            layout,

            "CRT Effect",

            config.get("crt_enabled", True)

        )


        self.scanlines_check = self._build_check_row(

            layout,

            "Scanlines",

            config.get("scanlines_enabled", True)

        )


        self.glitch_check = self._build_check_row(

            layout,

            "Glitch Effects",

            config.get("glitch_enabled", True)

        )


        self.animation_combo = self._build_combo_row(

            layout,

            "Animation Level",

            ["LOW", "MEDIUM", "HIGH"],

            config.get("animation_level", "MEDIUM")

        )


        button_row = QHBoxLayout()


        save_button = QPushButton("Save")

        save_button.clicked.connect(
            self._save
        )

        button_row.addWidget(
            save_button
        )


        close_button = QPushButton("Close")

        close_button.clicked.connect(
            self.hide
        )

        button_row.addWidget(
            close_button
        )


        layout.addLayout(
            button_row
        )


        #
        # Credit footer - always the last thing in the
        # settings box.
        #

        credit_label = QLabel(
            'Vibecoded by Samuel "Zenith" Schimmel (Madisico) 2026; '
            "This is open source software. "
            "Donations Appreciated, but Money Not Required."
        )

        credit_label.setWordWrap(True)

        credit_label.setStyleSheet(
            "font-size:11px; color:#5fb8c8; font-style:italic;"
            "border-top:1px solid #00ffff; padding-top:8px;"
        )

        layout.addWidget(
            credit_label
        )


        self.setStyleSheet(
            """
            QWidget {
                background:#101020;
                color:#00ffff;
                font-size:16px;
            }

            QDoubleSpinBox, QComboBox {
                background:#1a1a2e;
                border:2px solid #00ffff;
                border-radius:4px;
                padding:4px;
                color:#e0f8ff;
            }

            QCheckBox {
                spacing: 8px;
            }

            QPushButton {
                background:#004455;
                border:2px solid #00ffff;
                border-radius:6px;
                padding:8px;
                color:#e0f8ff;
            }

            QPushButton:hover {
                background:#006680;
            }
            """
        )



    def _build_spin_row(
        self,
        layout,
        label,
        minimum,
        maximum,
        value
    ):

        row = QHBoxLayout()

        row.addWidget(
            QLabel(label)
        )

        box = QDoubleSpinBox()

        box.setRange(
            minimum,
            maximum
        )

        box.setSingleStep(
            0.05
            if maximum <= 1.0
            else 1.0
        )

        box.setValue(
            value
        )

        row.addWidget(
            box
        )

        layout.addLayout(
            row
        )

        return box



    def _build_check_row(
        self,
        layout,
        label,
        checked
    ):

        checkbox = QCheckBox(
            label
        )

        checkbox.setChecked(
            checked
        )

        layout.addWidget(
            checkbox
        )

        return checkbox



    def _build_combo_row(
        self,
        layout,
        label,
        options,
        value
    ):

        row = QHBoxLayout()

        row.addWidget(
            QLabel(label)
        )

        combo = QComboBox()

        combo.addItems(
            options
        )

        if value in options:

            combo.setCurrentText(
                value
            )

        row.addWidget(
            combo
        )

        layout.addLayout(
            row
        )

        return combo



    def _save(self):

        sensitivity = self.sensitivity_box.value()

        trigger_boost = self.trigger_box.value()

        deadzone = self.deadzone_box.value()

        self.config["mouse_sensitivity"] = sensitivity

        self.config["trigger_boost"] = trigger_boost

        self.config["deadzone"] = deadzone

        self.settings_changed.emit(

            sensitivity,

            trigger_boost,

            deadzone

        )


        visual_settings = {

            "hud_enabled": self.hud_check.isChecked(),

            "crt_enabled": self.crt_check.isChecked(),

            "scanlines_enabled": self.scanlines_check.isChecked(),

            "glitch_enabled": self.glitch_check.isChecked(),

            "animation_level": self.animation_combo.currentText()

        }

        self.config.update(
            visual_settings
        )

        self.visual_settings_changed.emit(
            visual_settings
        )


        self.hide()
