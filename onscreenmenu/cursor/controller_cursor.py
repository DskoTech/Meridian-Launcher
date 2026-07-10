"""
onscreenmenu Controller Cursor

Handles controller-based mouse movement.

The controller moves the real Windows cursor.
The fake cursor overlay follows the real cursor
through InputTracker.

Button clicks (A / B) are NOT handled here anymore.
That is owned by InputManager, which decides
contextually whether A/B should click the real
cursor, activate a keyboard key, or select a menu
item. This class only ever moves the cursor and
performs the click when explicitly asked to.
"""


from PySide6.QtGui import QGuiApplication


from .mouse_events import (
    move_mouse,
    left_click,
    right_click,
    scroll_wheel
)




class ControllerCursor:


    def __init__(
        self,
        controller,
        config=None
    ):


        self.controller = controller

        config = config or {}


        #
        # Get screen dimensions
        #

        screen = QGuiApplication.primaryScreen()

        geometry = screen.geometry()

        self.width = geometry.width()

        self.height = geometry.height()


        #
        # Start cursor position
        #

        self.x = self.width / 2

        self.y = self.height / 2


        #
        # Movement tuning (configurable via Settings)
        #

        self.speed = config.get(
            "mouse_sensitivity",
            12.0
        )

        self.trigger_boost = config.get(
            "trigger_boost",
            4.0
        )

        self.deadzone = config.get(
            "deadzone",
            0.15
        )



    def apply_settings(
        self,
        sensitivity,
        trigger_boost,
        deadzone
    ):

        """
        Live-applies new values from the Settings dialog.
        """

        self.speed = sensitivity

        self.trigger_boost = trigger_boost

        self.deadzone = deadzone



    def update(self):

        """
        Called repeatedly by the main timer.

        Only handles analog stick movement now;
        clicks are dispatched by InputManager.
        """


        state = self.controller.state


        #
        # Controller stick movement
        #

        moving = (

            abs(state.left_x) > self.deadzone

            or

            abs(state.left_y) > self.deadzone

        )


        if not moving:

            return


        multiplier = 1


        #
        # Trigger acceleration
        #
        # Either trigger held applies the configured
        # boost multiplier for crossing large/4K screens
        # quickly.
        #

        if (

            state.left_trigger > 0.5

            or

            state.right_trigger > 0.5

        ):

            multiplier *= self.trigger_boost


        #
        # Apply movement
        #

        self.x += (

            state.left_x *

            self.speed *

            multiplier

        )

        self.y += (

            state.left_y *

            self.speed *

            multiplier

        )


        #
        # Clamp to screen
        #

        self.x = max(

            0,

            min(

                self.width,

                self.x

            )

        )

        self.y = max(

            0,

            min(

                self.height,

                self.y

            )

        )


        #
        # Move actual Windows cursor
        #

        move_mouse(

            self.x,

            self.y

        )



    def update_scroll(self):

        """
        Right stick vertical -> real mouse-wheel scroll, a
        substitute for a physical scroll wheel now that there's
        no browser to scroll via JavaScript.
        """

        state = self.controller.state

        if abs(state.right_y) > self.deadzone:

            scroll_wheel(
                int(state.right_y * -120)
            )


    def click_left(self):

        """
        Called by InputManager when A should act
        as a real left click (i.e. no keyboard or
        menu is claiming the button).
        """

        left_click()



    def click_right(self):

        """
        Called by InputManager when B should act
        as a real right click.
        """

        right_click()
