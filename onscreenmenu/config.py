"""
onscreenmenu Configuration

Stored under %LOCALAPPDATA%\\Meridian Launcher\\onscreenmenu\\config.json so
the app can read/write its settings regardless of where the exe itself
lives (Program Files is often not writable by a normal user), and so all
five Meridian apps keep their data together under one shared root folder.
"""

import json
import os
import shutil


APP_DIR_NAME = "Meridian Launcher"
APP_SUBDIR_NAME = "onscreenmenu"
CONFIG_FILENAME = "config.json"

# Pre-update installs stored config under %APPDATA%\DskoTech\onscreenmenu\ -
# migrated forward automatically the first time the new location is used.
_LEGACY_APP_DIR_NAME = "DskoTech"


def _config_dir():

    local_appdata = os.environ.get("LOCALAPPDATA")

    if not local_appdata:

        # Non-Windows / no LOCALAPPDATA fallback (dev/testing)

        local_appdata = os.path.expanduser("~")

    return os.path.join(
        local_appdata,
        APP_DIR_NAME,
        APP_SUBDIR_NAME
    )


def _legacy_config_dir():

    appdata = os.environ.get("APPDATA")

    if not appdata:

        appdata = os.path.expanduser("~")

    return os.path.join(
        appdata,
        _LEGACY_APP_DIR_NAME,
        APP_SUBDIR_NAME
    )


def _config_path():

    return os.path.join(
        _config_dir(),
        CONFIG_FILENAME
    )


def _migrate_legacy_config():

    old_path = os.path.join(_legacy_config_dir(), CONFIG_FILENAME)

    new_path = _config_path()

    if os.path.exists(old_path) and not os.path.exists(new_path):

        try:
            os.makedirs(_config_dir(), exist_ok=True)
            shutil.copy2(old_path, new_path)
        except OSError:
            pass


_migrate_legacy_config()


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
