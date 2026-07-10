"""
onscreenmenu Name Entry Popup

Used by both "Add Shortcut" (Y menu) and "Add Key Combo" (X menu)
to collect a name, capped at 20 characters, entered with the
onscreen keyboard.
"""

from ui.text_entry_popup import TextEntryPopup


MAX_NAME_LENGTH = 20


class NameEntryPopup(TextEntryPopup):


    def __init__(
        self,
        title="Name",
        parent=None
    ):

        super().__init__(
            title,
            placeholder="Enter a name...",
            max_length=MAX_NAME_LENGTH,
            parent=parent
        )


    def set_title(
        self,
        title
    ):

        self.title_label.setText(title)
