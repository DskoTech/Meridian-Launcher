"""
onscreenmenu Unified Pointer Manager

Combines:
- controller movement
- mouse movement
- touchscreen movement
"""


from PySide6.QtCore import QObject, Signal





class PointerManager(QObject):


    position_changed = Signal(
        int,
        int
    )



    def __init__(self):

        super().__init__()


        self.x = 0
        self.y = 0


        self.source = None





    def set_position(
        self,
        x,
        y,
        source="unknown"
    ):


        self.x = x
        self.y = y


        self.source = source


        self.position_changed.emit(

            int(x),

            int(y)

        )
