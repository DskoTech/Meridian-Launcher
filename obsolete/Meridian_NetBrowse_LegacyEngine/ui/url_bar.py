"""
CyberDeck URL Bar

Opened from the Tools (X) menu's "Enter URL"
option. Navigates the current tab.
"""


from ui.text_entry_popup import TextEntryPopup




class UrlBar(TextEntryPopup):


    def __init__(
        self,
        parent=None
    ):

        super().__init__(

            "URL",

            placeholder="https://...",

            parent=parent

        )
