"""
X Button Menu
"""


from menus.menu_base import CyberMenu




class ToolsMenu(CyberMenu):


    def __init__(self, on_select=None, boxed=False):

        items = ["Refresh", "Previous Page", "Next Page"]

        if not boxed:
            # New Tab and Enter URL (the address/search entry point) only
            # make sense for a standalone, freely-browsing instance - not
            # when Meridian Launcher has this boxed into a section or a
            # single-site webapp plugin.
            items += ["Enter URL", "New Tab"]

        items.append("Close Tab")
        items.append("Exit Program" if boxed else "Close Browser")

        super().__init__(

            "Tools",

            items,

            on_select=on_select

        )
