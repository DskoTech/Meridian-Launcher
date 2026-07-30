"""
Y Button Menu
"""


from menus.menu_base import CyberMenu




class BrowserMenu(CyberMenu):


    def __init__(self, on_select=None):

        super().__init__(

            "Browser",

            [

                "History",

                "Downloads",

                "Bookmarks",

                "Translate",

                "Settings",

                "Find In Page"

            ],

            on_select=on_select

        )
