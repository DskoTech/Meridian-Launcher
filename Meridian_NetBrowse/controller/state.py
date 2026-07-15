"""
Controller State Object

Shared between polling thread
and application.
"""


from dataclasses import dataclass



@dataclass
class ControllerState:


    connected: bool=False


    # Analog sticks

    left_x: float=0.0
    left_y: float=0.0

    right_x: float=0.0
    right_y: float=0.0


    # Triggers

    left_trigger: float=0.0
    right_trigger: float=0.0


    # Buttons

    a: bool=False
    b: bool=False
    x: bool=False
    y: bool=False


    start: bool=False
    select: bool=False


    left_shoulder: bool=False
    right_shoulder: bool=False


    # Stick clicks

    l3: bool=False
    r3: bool=False


    # D-pad

    dpad_up: bool=False
    dpad_down: bool=False
    dpad_left: bool=False
    dpad_right: bool=False
