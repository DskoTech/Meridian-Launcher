"""
X Button Menu
"""


from menus.menu_base import CyberMenu




class ToolsMenu(CyberMenu):


    def __init__(self, on_select=None):

        super().__init__(

            "Tools",

            [

                "Refresh",

                "Enter URL",

                "Previous Page",

                "Next Page",

                "New Tab",

                "Close Tab",

                "Close Browser"

            ],

            on_select=on_select

        )
