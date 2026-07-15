"""
CyberDeck Text Entry Popup

Shared base for any popup that needs:
- A real (mouse/physical-keyboard editable) text field
- The shared universal onscreen keyboard
- Cyberpunk styling matching CyberMenu

Used by:
- SearchWindow  (Start button)
- UrlBar        (Enter URL)
- FindBar       (Find In Page)
"""


from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel,
    QLineEdit
)

from PySide6.QtCore import Qt, Signal




class TextEntryPopup(QWidget):


    #
    # Emitted with the submitted text
    # when the user presses Enter / the
    # onscreen keyboard's ENTER key.
    #

    submitted = Signal(str)



    def __init__(
        self,
        title,
        placeholder="",
        parent=None
    ):

        super().__init__(parent)

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

        self.line_edit.returnPressed.connect(
            self._handle_submit
        )

        layout.addWidget(
            self.line_edit
        )


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


        #
        # Bound once a keyboard_window is attached
        # via attach_keyboard()
        #

        self.keyboard_window = None



    def attach_keyboard(
        self,
        keyboard_window
    ):

        """
        Connects this popup's text field to the
        shared universal onscreen keyboard.

        The TextInputManager is shared across every
        popup, so both sync directions are guarded to
        only act when this popup is the current target -
        otherwise typing in one popup would leak into
        the others' line edits.
        """

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

            #
            # Keep the virtual keyboard and the real
            # line edit in sync regardless of which
            # input method the person uses.
            #

            text_manager.current_text = initial_text

            text_manager.set_target(
                self.line_edit
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

        """
        The onscreen keyboard already calls
        target.setText(), but this keeps things
        correct even if the target changes mid-type.

        Guarded so only the popup currently bound to
        the shared keyboard reacts.
        """

        if not self._is_active_target():

            return

        if self.line_edit.text() != text:

            self.line_edit.setText(
                text
            )



    def _sync_to_keyboard(
        self,
        text
    ):

        """
        Physical keyboard typing updates the shared
        TextInputManager so the onscreen keyboard
        picks up right where physical typing left off.

        Guarded so a background popup's line edit
        (which shouldn't normally receive events while
        hidden, but just in case) can't hijack the
        shared keyboard state.
        """

        if not self._is_active_target():

            return

        self.keyboard_window.text_manager.current_text = text



    def _handle_submit(self):

        text = self.line_edit.text()

        self.submitted.emit(
            text
        )
