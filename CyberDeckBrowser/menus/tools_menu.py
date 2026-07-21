"""
X Button Menu
"""


from menus.menu_base import CyberMenu




class ToolsMenu(CyberMenu):


    def __init__(self, on_select=None, boxed=False):

        # New Tab used to be excluded here too ("only makes sense for a
        # standalone, freely-browsing instance"), but the Browser section
        # is exactly that - a freely-browsing instance, just boxed into
        # Meridian Launcher's list-frame instead of fullscreen. The tab
        # bar (BrowserTabs) was never actually hidden for boxed mode -
        # only minimal_menu (single-site webapp plugins, where tabs
        # genuinely don't make sense) hides it - so this was the only
        # thing actually stopping multiple tabs from being usable there.
        items = ["Refresh", "Previous Page", "Next Page", "New Tab"]

        if not boxed:
            # Enter URL (the address/search entry point) only makes sense
            # for a standalone instance - the boxed Browser section is
            # always navigated via links/shortcuts Meridian Launcher hands
            # it, not manual address entry.
            items += ["Enter URL"]

        items.append("Close Tab")
        items.append("Exit Program" if boxed else "Close Browser")

        super().__init__(

            "Tools",

            items,

            on_select=on_select

        )
