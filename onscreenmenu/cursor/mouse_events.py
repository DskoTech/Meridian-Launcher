"""
onscreenmenu Mouse Event Injection

Windows mouse movement and clicks.
"""


import ctypes


user32 = ctypes.windll.user32





MOUSEEVENTF_MOVE = 0x0001

MOUSEEVENTF_ABSOLUTE = 0x8000

MOUSEEVENTF_LEFTDOWN = 0x0002

MOUSEEVENTF_LEFTUP = 0x0004

MOUSEEVENTF_RIGHTDOWN = 0x0008

MOUSEEVENTF_RIGHTUP = 0x0010

MOUSEEVENTF_WHEEL = 0x0800





def move_mouse(
    x,
    y
):

    """
    Move Windows cursor using
    absolute screen coordinates.
    """


    screen_width = user32.GetSystemMetrics(0)

    screen_height = user32.GetSystemMetrics(1)



    absolute_x = int(

        x * 65535 / screen_width

    )


    absolute_y = int(

        y * 65535 / screen_height

    )



    user32.mouse_event(

        MOUSEEVENTF_MOVE |

        MOUSEEVENTF_ABSOLUTE,

        absolute_x,

        absolute_y,

        0,

        0

    )





def left_click():

    """
    Windows left click.
    """


    user32.mouse_event(

        MOUSEEVENTF_LEFTDOWN,

        0,

        0,

        0,

        0

    )


    user32.mouse_event(

        MOUSEEVENTF_LEFTUP,

        0,

        0,

        0,

        0

    )





def right_click():

    """
    Windows right click.
    """


    user32.mouse_event(

        MOUSEEVENTF_RIGHTDOWN,

        0,

        0,

        0,

        0

    )


    user32.mouse_event(

        MOUSEEVENTF_RIGHTUP,

        0,

        0,

        0,

        0

    )




def scroll_wheel(
    amount
):

    """
    Real Windows mouse-wheel scroll. `amount` follows the
    standard WHEEL_DELTA convention (120 = one notch up,
    -120 = one notch down).
    """

    user32.mouse_event(

        MOUSEEVENTF_WHEEL,

        0,

        0,

        int(amount),

        0

    )
