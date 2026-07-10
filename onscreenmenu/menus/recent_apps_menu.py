"""
Select Button Menu (Recent Apps)
"""

from menus.menu_base import CyberMenu


class RecentAppsMenu(CyberMenu):


    def __init__(
        self,
        titles,
        on_select=None
    ):

        super().__init__(
            "Recent Apps",
            titles or ["No Recent Apps"],
            on_select=on_select
        )
