"""
CyberDeck Keyboard Layout

Defines:
- Key positions
- Display labels
- Inserted text
- Special actions

Used by:
- KeyboardWidget
- Controller navigation
- Mouse/touch selection
"""

# Key types:
#
# character:
#     inserts text
#
# action:
#     performs a command


def _row(chars):
    return [
        {"id": c, "label": c, "value": c, "type": "character"}
        for c in chars
    ]


KEYBOARD_LAYOUT = [

    # --------------------------------------------------
    # Symbol row (always visible, top row)
    # --------------------------------------------------

    _row(
        list("!@#$%^&*()_+;'[],./\\{}") 
    ),


    # --------------------------------------------------
    # Number row
    # --------------------------------------------------

    _row(
        list("1234567890")
    ),


    # --------------------------------------------------
    # QWERTY row
    # --------------------------------------------------

    [
        {"id": c, "label": c.upper(), "value": c, "type": "character"}
        for c in "qwertyuiop"
    ],


    # --------------------------------------------------
    # Home row
    # --------------------------------------------------

    [
        {"id": c, "label": c.upper(), "value": c, "type": "character"}
        for c in "asdfghjkl"
    ],


    # --------------------------------------------------
    # Bottom letter row (microphone at the end)
    # --------------------------------------------------

    [
        {"id": c, "label": c.upper(), "value": c, "type": "character"}
        for c in "zxcvbnm"
    ] + [
        {
            "id": "microphone",
            "label": "\U0001F3A4",
            "value": None,
            "type": "action"
        }
    ],


    # --------------------------------------------------
    # Function row
    # --------------------------------------------------

    [

        {
            "id": "shift",
            "label": "SHIFT",
            "value": None,
            "type": "action"
        },

        {
            "id": "space",
            "label": "SPACE",
            "value": " ",
            "type": "character"
        },

        {
            "id": "backspace",
            "label": "BACK",
            "value": None,
            "type": "action"
        },

        {
            "id": "enter",
            "label": "ENTER",
            "value": None,
            "type": "action"
        },

        {
            "id": "dotcom",
            "label": ".com",
            "value": ".com",
            "type": "character"
        },

        {
            "id": "gmail",
            "label": "@gmail.com",
            "value": "@gmail.com",
            "type": "character"
        }

    ]

]


def get_key(
    row,
    column
):

    """
    Safely retrieve a key.
    """

    try:

        return KEYBOARD_LAYOUT[row][column]

    except IndexError:

        return None


def keyboard_rows():

    """
    Return number of rows.
    """

    return len(KEYBOARD_LAYOUT)
