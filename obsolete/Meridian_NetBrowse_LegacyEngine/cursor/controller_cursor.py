"""
CyberDeck Controller Cursor

Handles controller-based mouse movement.

The controller moves the real Windows cursor
directly. There is no separate fake-cursor overlay
anymore - it caused a doubled/trailing visual, so
this class now just moves the one real cursor.

Button clicks (A / B) are NOT handled here anymore.
That is owned by InputManager, which decides
contextually whether A/B should click the real
cursor, activate a keyboard key, or select a menu
item. This class only ever moves the cursor and
performs the click when explicitly asked to.
"""


import ctypes


from .mouse_events import (
    move_mouse,
    left_click,
    right_click
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
        # Get screen dimensions - in the SAME (physical-pixel) coordinate
        # space move_mouse() uses (ctypes GetSystemMetrics), not Qt's
        # QScreen.geometry(), which reports DPI-scaled LOGICAL pixels for
        # a DPI-aware process. On a 4K display at 200% Windows scaling
        # those disagree by exactly 2x in each axis (1920x1080 logical vs
        # 3840x2160 physical) - tracking position against the smaller
        # logical bounds while move_mouse() normalizes against the larger
        # physical ones meant the cursor could only ever reach the
        # top-left quarter of the actual screen, regardless of how far
        # the stick was pushed.
        #

        user32 = ctypes.windll.user32

        self.width = user32.GetSystemMetrics(0)

        self.height = user32.GetSystemMetrics(1)


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
            30.0
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
