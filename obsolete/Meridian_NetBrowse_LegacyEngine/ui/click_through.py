"""
CyberDeck Click-Through Helper

Windows-specific: makes an overlay widget invisible
to mouse hit testing, so clicks pass through to
whatever is beneath it (the browser, menus, etc).

Used by HUDOverlay so it stays
purely decorative and never intercept input.
"""


import ctypes




def make_click_through(widget):

    hwnd = int(
        widget.winId()
    )

    GWL_EXSTYLE = -20

    WS_EX_TRANSPARENT = 0x00000020

    WS_EX_NOACTIVATE = 0x08000000

    style = ctypes.windll.user32.GetWindowLongW(

        hwnd,

        GWL_EXSTYLE

    )

    ctypes.windll.user32.SetWindowLongW(

        hwnd,

        GWL_EXSTYLE,

        style |
        WS_EX_TRANSPARENT |
        WS_EX_NOACTIVATE

    )
