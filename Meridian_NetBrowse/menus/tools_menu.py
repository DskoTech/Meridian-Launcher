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

                # "Exit Program": Meridian NetBrowse is always launched
                # boxed by Meridian Launcher's Browser section, never
                # standalone — this simply closes the window/process;
                # Meridian Launcher's watcher thread notices the exit and
                # moves the section selector back to the Sections bar,
                # restoring its own controls.
                "Exit Program"

            ],

            on_select=on_select

        )
