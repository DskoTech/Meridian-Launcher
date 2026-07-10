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
            440,
            520
        )


        layout = QVBoxLayout(self)


        layout.addWidget(
            QLabel("SETTINGS")
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
