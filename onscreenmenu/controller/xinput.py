"""
onscreenmenu XInput Reader

Direct Windows XInput DLL interface.
No external package required.
"""


import ctypes
from ctypes import wintypes


# XInput DLL

try:

    xinput = ctypes.WinDLL(
        "xinput1_4.dll"
    )

except:

    try:

        xinput = ctypes.WinDLL(
            "xinput1_3.dll"
        )

    except:

        xinput = None



# Controller buttons

BUTTON_DPAD_UP        = 0x0001
BUTTON_DPAD_DOWN      = 0x0002
BUTTON_DPAD_LEFT      = 0x0004
BUTTON_DPAD_RIGHT     = 0x0008

BUTTON_START          = 0x0010
BUTTON_BACK           = 0x0020

BUTTON_LEFT_SHOULDER  = 0x0100
BUTTON_RIGHT_SHOULDER = 0x0200

BUTTON_A              = 0x1000
BUTTON_B              = 0x2000
BUTTON_X              = 0x4000
BUTTON_Y              = 0x8000



class XINPUT_GAMEPAD(ctypes.Structure):

    _fields_ = [

        (
            "wButtons",
            wintypes.WORD
        ),

        (
            "bLeftTrigger",
            ctypes.c_ubyte
        ),

        (
            "bRightTrigger",
            ctypes.c_ubyte
        ),

        (
            "sThumbLX",
            ctypes.c_short
        ),

        (
            "sThumbLY",
            ctypes.c_short
        ),

        (
            "sThumbRX",
            ctypes.c_short
        ),

        (
            "sThumbRY",
            ctypes.c_short
        )

    ]



class XINPUT_STATE(ctypes.Structure):

    _fields_ = [

        (
            "dwPacketNumber",
            wintypes.DWORD
        ),

        (
            "Gamepad",
            XINPUT_GAMEPAD
        )

    ]



if xinput:

    xinput.XInputGetState.argtypes = [

        wintypes.DWORD,
        ctypes.POINTER(XINPUT_STATE)

    ]



    xinput.XInputGetState.restype = wintypes.DWORD





class XInputReader:


    def __init__(self):

        self.connected=False



    def get_state(self):


        if not xinput:

            return None



        state=XINPUT_STATE()



        result=xinput.XInputGetState(

            0,

            ctypes.byref(state)

        )



        if result != 0:

            self.connected=False

            return None



        self.connected=True


        return state
