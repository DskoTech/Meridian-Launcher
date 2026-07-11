"""
CyberDeck Browser Configuration
"""


import json
import os

from paths import DATA_DIR


CONFIG_FILE = os.path.join(
    DATA_DIR,
    "cyberdeck_config.json"
)


DEFAULTS = {

    "homepage":
        "https://www.google.com",

    "fullscreen":
        True,

    "zoom":
        1.0,

    "search_engine":
        "https://www.google.com/search?q=",

    "mouse_sensitivity":
        30.0,

    "trigger_boost":
        4.0,

    "deadzone":
        0.15,

    "hud_enabled":
        True,

    "crt_enabled":
        True,

    "scanlines_enabled":
        True,

    "glitch_enabled":
        True,

    "animation_level":
        "MEDIUM",

    "cyberpunk_prompt_shown":
        False

}



def load_config():

    if not os.path.exists(CONFIG_FILE):

        save_config(DEFAULTS)
        return DEFAULTS.copy()


    try:

        with open(CONFIG_FILE, "r") as f:

            data=json.load(f)


        for key,value in DEFAULTS.items():

            if key not in data:

                data[key]=value


        return data


    except Exception:

        return DEFAULTS.copy()



def save_config(data):

    with open(CONFIG_FILE,"w") as f:

        json.dump(
            data,
            f,
            indent=4
        )
