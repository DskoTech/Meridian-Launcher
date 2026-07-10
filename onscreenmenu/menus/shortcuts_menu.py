"""
Y Button Menu (Shortcuts)
"""

from menus.menu_base import CyberMenu


class ShortcutsMenu(CyberMenu):


    def __init__(
        self,
        items,
        on_select=None
    ):

        super().__init__(
            "Shortcuts",
            items,
            on_select=on_select
        )
