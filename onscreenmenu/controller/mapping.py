"""
Controller Mapping

Converts XInput values
into onscreenmenu commands.
"""


def normalize_axis(
    value,
    deadzone=0.15
):


    if abs(value)<deadzone:

        return 0.0


    return value



def map_button(
    buttons,
    name
):

    return getattr(
        buttons,
        name,
        False
    )
