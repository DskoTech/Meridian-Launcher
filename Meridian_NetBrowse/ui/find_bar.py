"""
CyberDeck Find In Page Bar

Opened from the Browser (Y) menu's
"Find In Page" option.
"""


from ui.text_entry_popup import TextEntryPopup




class FindBar(TextEntryPopup):


    def __init__(
        self,
        parent=None
    ):

        super().__init__(

            "FIND IN PAGE",

            placeholder="Find on this page...",

            parent=parent

        )
