"""
CyberDeck Pointer Manager

Unifies real cursor position updates (from
physical mouse movement or controller-driven
movement) into a single signal the fake cursor
overlay listens to.
"""


from PySide6.QtCore import QObject, Signal




class PointerManager(QObject):


    position_changed = Signal(
        float,
        float
    )



    def __init__(self):

        super().__init__()

        self.x = 0.0

        self.y = 0.0



    def set_position(
        self,
        x,
        y
    ):

        self.x = x

        self.y = y

        self.position_changed.emit(
            x,
            y
        )
