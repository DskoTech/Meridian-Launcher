"""
X Button Menu (Key Combos)
"""

from menus.menu_base import CyberMenu


class KeyComboMenu(CyberMenu):


    def __init__(
        self,
        items,
        on_select=None
    ):

        super().__init__(
            "Key Combos",
            items,
            on_select=on_select
        )
