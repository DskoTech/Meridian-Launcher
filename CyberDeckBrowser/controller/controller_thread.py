"""
CyberDeck Controller Thread

Runs gamepad polling in a separate thread.

Provides:
- Analog stick movement
- D-pad events
- Controller buttons
- Shoulder buttons
- Triggers

UI code should connect to signals.
"""


from PySide6.QtCore import (
    QThread,
    Signal
)

import time

from controller.state import ControllerState



try:

    import pygame

    GAMEPAD_AVAILABLE = True


except ImportError:

    GAMEPAD_AVAILABLE = False





class ControllerThread(QThread):


    #
    # Buttons
    #

    a_pressed = Signal()

    b_pressed = Signal()

    x_pressed = Signal()

    y_pressed = Signal()



    start_pressed = Signal()

    select_pressed = Signal()



    lb_pressed = Signal()

    rb_pressed = Signal()


    l3_pressed = Signal()

    r3_pressed = Signal()



    #
    # D-pad
    #

    dpad_up = Signal()

    dpad_down = Signal()

    dpad_left = Signal()

    dpad_right = Signal()



    #
    # Analog movement
    #

    left_stick = Signal(
        float,
        float
    )


    right_stick = Signal(
        float,
        float
    )


    #
    # Triggers
    #

    left_trigger = Signal(
        float
    )


    right_trigger = Signal(
        float
    )





    def __init__(
        self,
        parent=None
    ):

        super().__init__(parent)



        self.running = True



        self.controller = None



        self.last_buttons = {}

        self.current_buttons = {}

        self.state = ControllerState()





    def initialize_controller(self):


        if not GAMEPAD_AVAILABLE:

            return



        pygame.init()


        pygame.joystick.init()



        if pygame.joystick.get_count() > 0:


            self.controller = pygame.joystick.Joystick(0)


            self.controller.init()





    def button_pressed(
        self,
        button
    ):


        return (

            self.last_buttons.get(
                button,
                False
            )

            and

            not self.current_buttons.get(
                button,
                False
            )

        )





    def run(self):


        self.initialize_controller()



        while self.running:


            if not self.controller:

                self.state.connected = False

                time.sleep(
                    .5
                )

                continue



            pygame.event.pump()



            self.current_buttons = {}

            self.state.connected = True



            #
            # Standard Xbox layout
            #

            for i in range(

                self.controller.get_numbuttons()

            ):


                self.current_buttons[i] = (

                    self.controller.get_button(i)

                )



            self.state.a = self.current_buttons.get(0, False)
            self.state.b = self.current_buttons.get(1, False)
            self.state.x = self.current_buttons.get(2, False)
            self.state.y = self.current_buttons.get(3, False)

            self.state.start = self.current_buttons.get(7, False)
            self.state.select = self.current_buttons.get(6, False)

            self.state.left_shoulder = self.current_buttons.get(4, False)
            self.state.right_shoulder = self.current_buttons.get(5, False)

            self.state.l3 = self.current_buttons.get(8, False)
            self.state.r3 = self.current_buttons.get(9, False)




            #
            # Buttons
            #

            self.check_button(
                0,
                self.a_pressed
            )


            self.check_button(
                1,
                self.b_pressed
            )


            self.check_button(
                2,
                self.x_pressed
            )


            self.check_button(
                3,
                self.y_pressed
            )


            self.check_button(
                7,
                self.start_pressed
            )


            self.check_button(
                6,
                self.select_pressed
            )


            self.check_button(
                4,
                self.lb_pressed
            )


            self.check_button(
                5,
                self.rb_pressed
            )


            self.check_button(
                8,
                self.l3_pressed
            )


            self.check_button(
                9,
                self.r3_pressed
            )





            #
            # Analog sticks
            #

            lx = self.controller.get_axis(0)

            ly = self.controller.get_axis(1)


            rx = self.controller.get_axis(2)

            ry = self.controller.get_axis(3)



            deadzone = .15



            if abs(lx) < deadzone:

                lx = 0


            if abs(ly) < deadzone:

                ly = 0


            if abs(rx) < deadzone:

                rx = 0


            if abs(ry) < deadzone:

                ry = 0


            self.state.left_x = lx
            self.state.left_y = ly

            self.state.right_x = rx
            self.state.right_y = ry



            self.left_stick.emit(
                lx,
                ly
            )


            self.right_stick.emit(
                rx,
                ry
            )





            #
            # Triggers
            #

            self.left_trigger.emit(

                self.controller.get_axis(4)

            )


            self.right_trigger.emit(

                self.controller.get_axis(5)

            )


            self.state.left_trigger = self.controller.get_axis(4)
            self.state.right_trigger = self.controller.get_axis(5)





            #
            # D-pad
            #

            hat = self.controller.get_hat(0)


            self.state.dpad_up = hat[1] == 1
            self.state.dpad_down = hat[1] == -1

            self.state.dpad_left = hat[0] == -1
            self.state.dpad_right = hat[0] == 1


            if hat[1] == 1:

                self.dpad_up.emit()


            elif hat[1] == -1:

                self.dpad_down.emit()



            if hat[0] == -1:

                self.dpad_left.emit()


            elif hat[0] == 1:

                self.dpad_right.emit()





            self.last_buttons = self.current_buttons.copy()



            time.sleep(
                .016
            )





    def check_button(
        self,
        index,
        signal
    ):


        if (

            self.current_buttons.get(index)

            and

            not self.last_buttons.get(index)

        ):

            signal.emit()





    def stop(self):


        self.running = False


        self.quit()

        self.wait()
