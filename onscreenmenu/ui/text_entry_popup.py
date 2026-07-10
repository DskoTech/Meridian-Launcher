"""
onscreenmenu Text Entry Popup

Shared base for any popup that needs:
- A real (mouse/physical-keyboard editable) text field
- The shared onscreen keyboard, bound to this popup's field
  (NOT system passthrough - typing here only fills this box)
- Cyberpunk styling

Used by:
- NameEntryPopup (naming a new shortcut / key combo)
"""

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel,
    QLineEdit
)

from PySide6.QtCore import Qt, Signal


class TextEntryPopup(QWidget):


    submitted = Signal(str)


    def __init__(
        self,
        title,
        placeholder="",
        max_length=None,
        parent=None
    ):

        super().__init__(parent)

        self.max_length = max_length

        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.Tool
        )

        self.resize(
            560,
            140
        )

        layout = QVBoxLayout(self)

        self.title_label = QLabel(title)

        layout.addWidget(
            self.title_label
        )

        self.line_edit = QLineEdit()

        self.line_edit.setPlaceholderText(
            placeholder
        )

        if max_length is not None:

            self.line_edit.setMaxLength(
                max_length
            )

        self.line_edit.returnPressed.connect(
            self._handle_submit
        )

        layout.addWidget(
            self.line_edit
        )

        self.hint_label = QLabel("")

        self.hint_label.setStyleSheet(
            "color:#5599aa; font-size:12px;"
        )

        layout.addWidget(
            self.hint_label
        )

        if max_length is not None:

            self.line_edit.textChanged.connect(
                self._update_hint
            )

            self._update_hint()

        self.setStyleSheet(
            """
            QWidget {
                background:#101020;
                color:#00ffff;
                font-size:18px;
            }

            QLabel {
                font-size:16px;
                color:#00ffff;
            }

            QLineEdit {
                background:#1a1a2e;
                border:2px solid #00ffff;
                border-radius:6px;
                padding:8px;
                color:#e0f8ff;
                font-size:20px;
            }
            """
        )

        self.keyboard_window = None


    def _update_hint(self):

        if self.max_length is None:

            return

        self.hint_label.setText(

            str(len(self.line_edit.text()))
            + " / "
            + str(self.max_length)

        )


    def attach_keyboard(
        self,
        keyboard_window
    ):

        self.keyboard_window = keyboard_window

        text_manager = keyboard_window.text_manager

        text_manager.text_changed.connect(
            self._sync_from_keyboard
        )

        self.line_edit.textEdited.connect(
            self._sync_to_keyboard
        )


    def open_with_keyboard(
        self,
        initial_text=""
    ):

        self.line_edit.setText(
            initial_text
        )

        self.line_edit.selectAll()

        if self.keyboard_window:

            text_manager = self.keyboard_window.text_manager

            text_manager.current_text = initial_text

            text_manager.set_target(
                self.line_edit,
                max_length=self.max_length
            )

            self.keyboard_window.show_keyboard()

        self.show()

        self.line_edit.setFocus()


    def close_popup(self):

        if self.keyboard_window:

            self.keyboard_window.hide_keyboard()

            self.keyboard_window.text_manager.set_target(
                None
            )

        self.hide()


    def _is_active_target(self):

        return (

            self.keyboard_window is not None

            and

            self.keyboard_window.text_manager.target is self.line_edit

        )


    def _sync_from_keyboard(
        self,
        text
    ):

        if not self._is_active_target():

            return

        if self.line_edit.text() != text:

            self.line_edit.setText(text)


    def _sync_to_keyboard(
        self,
        text
    ):

        if not self._is_active_target():

            return

        self.keyboard_window.text_manager.current_text = text


    def _handle_submit(self):

        text = self.line_edit.text()

        self.submitted.emit(text)
