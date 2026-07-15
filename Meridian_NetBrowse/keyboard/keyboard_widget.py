"""
CyberDeck Keyboard Widget

DPI-aware cyberpunk onscreen keyboard.

Handles:
- Rendering
- Controller selection highlight
- Mouse/touch selection
- Key activation signals
- Show/hide overlay

Does NOT handle:
- Text insertion
- Browser focus
- Voice input

Those belong to TextInputManager.
"""


from PySide6.QtWidgets import QWidget

from PySide6.QtCore import (
    Qt,
    Signal
)

from PySide6.QtGui import (
    QPainter,
    QColor,
    QPen,
    QBrush,
    QGuiApplication
)


from .keyboard_layout import (
    KEYBOARD_LAYOUT
)





class KeyboardWidget(QWidget):


    #
    # Sends key dictionaries
    #

    key_pressed = Signal(dict)





    def __init__(
        self,
        parent=None
    ):

        super().__init__(parent)



        self.selected_row = 0

        self.selected_col = 0



        self.visible = False



        self.scale = 1.0



        #
        # Window behavior
        #

        self.setWindowFlags(

            Qt.FramelessWindowHint |

            Qt.WindowStaysOnTopHint |

            Qt.Tool |

            Qt.WindowDoesNotAcceptFocus

        )



        self.setAttribute(

            Qt.WA_TranslucentBackground

        )



        self.setAttribute(

            Qt.WA_ShowWithoutActivating

        )



        self.update_geometry()





    def update_geometry(self):

        """
        Resize keyboard for current monitor.
        """


        screen = QGuiApplication.primaryScreen()


        if not screen:

            return



        geometry = screen.virtualGeometry()


        self.scale = screen.devicePixelRatio()



        width = int(

            geometry.width() * .85

        )


        height = int(

            geometry.height() * .35

        )



        x = geometry.x() + (

            geometry.width() - width

        ) // 2



        y = geometry.y() + (

            geometry.height() - height

        ) - 50



        self.setGeometry(

            x,

            y,

            width,

            height

        )





    def show_keyboard(self):

        self.visible = True

        self.update_geometry()

        self.show()

        self.raise_()





    def hide_keyboard(self):

        self.visible = False

        self.hide()





    def toggle(self):

        if self.visible:

            self.hide_keyboard()

        else:

            self.show_keyboard()





    def move_selection(
        self,
        dx,
        dy
    ):

        """
        Controller navigation.
        """


        new_row = self.selected_row + dy



        new_row = max(

            0,

            min(

                len(KEYBOARD_LAYOUT)-1,

                new_row

            )

        )



        new_col = self.selected_col + dx



        new_col = max(

            0,

            min(

                len(KEYBOARD_LAYOUT[new_row])-1,

                new_col

            )

        )



        self.selected_row = new_row

        self.selected_col = new_col



        self.update()





    def activate_selected(self):

        key = KEYBOARD_LAYOUT[

            self.selected_row

        ][

            self.selected_col

        ]


        self.key_pressed.emit(

            key

        )





    def mousePressEvent(
        self,
        event
    ):


        if event.button() != Qt.LeftButton:

            return



        width = self.width()

        height = self.height()



        rows = len(KEYBOARD_LAYOUT)



        row_height = height / rows



        row = int(

            event.position().y()

            /

            row_height

        )



        if row >= rows:

            return



        cols = len(

            KEYBOARD_LAYOUT[row]

        )



        col_width = width / cols



        col = int(

            event.position().x()

            /

            col_width

        )



        if col >= cols:

            return



        self.selected_row = row

        self.selected_col = col



        self.activate_selected()





    def paintEvent(
        self,
        event
    ):


        painter = QPainter(

            self

        )


        painter.setRenderHint(

            QPainter.Antialiasing

        )



        width = self.width()

        height = self.height()



        rows = len(KEYBOARD_LAYOUT)



        row_height = height / rows





        for r, row in enumerate(KEYBOARD_LAYOUT):


            cols = len(row)


            col_width = width / cols



            for c, key in enumerate(row):


                x = c * col_width

                y = r * row_height



                selected = (

                    r == self.selected_row

                    and

                    c == self.selected_col

                )



                if selected:


                    painter.setBrush(

                        QBrush(

                            QColor(
                                0,
                                180,
                                255,
                                120
                            )

                        )

                    )


                else:


                    painter.setBrush(

                        QBrush(

                            QColor(
                                20,
                                20,
                                35,
                                220
                            )

                        )

                    )



                painter.setPen(

                    QPen(

                        QColor(
                            0,
                            255,
                            255
                        ),

                        2

                    )

                )



                painter.drawRoundedRect(

                    int(x+4),

                    int(y+4),

                    int(col_width-8),

                    int(row_height-8),

                    8,

                    8

                )



                painter.setPen(

                    QColor(
                        220,
                        240,
                        255
                    )

                )


                painter.drawText(

                    int(x),

                    int(y),

                    int(col_width),

                    int(row_height),

                    Qt.AlignCenter,

                    key["label"]

                )



        painter.end()
