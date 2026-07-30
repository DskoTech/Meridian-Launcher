"""
CyberDeck Search Window

Opened with the Start button.

Submits a query to the configured default
search engine in the current tab.
"""


from ui.text_entry_popup import TextEntryPopup




class SearchWindow(TextEntryPopup):


    def __init__(
        self,
        search_engine,
        parent=None
    ):

        super().__init__(

            "SEARCH",

            placeholder="Search the web...",

            parent=parent

        )

        self.search_engine = search_engine



    def set_search_engine(
        self,
        search_engine
    ):

        self.search_engine = search_engine



    def build_url(
        self,
        query
    ):

        query = query.strip()

        if not query:

            return None

        return self.search_engine + query
