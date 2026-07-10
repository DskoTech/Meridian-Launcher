"""
onscreenmenu Configuration

Stored under %APPDATA%\\DskoTech\\onscreenmenu\\config.json so the
app can read/write its settings regardless of where the exe itself
lives (Program Files is often not writable by a normal user).
"""

import json
import os


APP_DIR_NAME = "DskoTech"
APP_SUBDIR_NAME = "onscreenmenu"
CONFIG_FILENAME = "config.json"


def _config_dir():

    appdata = os.environ.get("APPDATA")

    if not appdata:

        # Non-Windows / no APPDATA fallback (dev/testing)

        appdata = os.path.expanduser("~")

    return os.path.join(
        appdata,
        APP_DIR_NAME,
        APP_SUBDIR_NAME
    )


def _config_path():

    return os.path.join(
        _config_dir(),
        CONFIG_FILENAME
    )


DEFAULTS = {

    "fullscreen":
        True,

    "mouse_sensitivity":
        12.0,

    "trigger_boost":
        4.0,

    "deadzone":
        0.15,

    "first_run_done":
        False,

    "skip_install_prompt":
        False,

    # Y-button custom shortcuts.
    # "Meridian Launcher" is NOT stored here - it is always the
    # first, non-removable entry, handled specially in code.
    "shortcuts":
        [],

    # X-button custom key combos.
    "key_combos":
        []

}


def load_config():

    path = _config_path()

    if not os.path.exists(path):

        data = DEFAULTS.copy()

        save_config(data)

        return data

    try:

        with open(path, "r") as f:

            data = json.load(f)

        for key, value in DEFAULTS.items():

            if key not in data:

                data[key] = value

        return data

    except Exception:

        return DEFAULTS.copy()


def save_config(data):

    directory = _config_dir()

    os.makedirs(
        directory,
        exist_ok=True
    )

    with open(_config_path(), "w") as f:

        json.dump(
            data,
            f,
            indent=4
        )
