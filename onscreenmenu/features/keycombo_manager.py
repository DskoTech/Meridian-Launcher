"""
onscreenmenu Key Combo Manager (X button)

The X menu starts with two fixed, non-removable entries -
"Virtual Keyboard" (toggles Windows' on-screen keyboard - moved here
from its own dedicated Start button binding, which now does nothing)
and "Close Onscreenmenu" (quits the app) - followed by any
already-configured key combos (1-3 physical keys each, edited via
config.json; there's no longer an in-menu "Add"/"Remove" flow for
these - see the module history below).

Running a saved combo sends it once, then a global cooldown
briefly blocks re-triggering (any combo) to avoid accidental
repeats/hardware chatter.
"""

import time

import keyboard


CLOSE_APP_LABEL = "Close Onscreenmenu"
VIRTUAL_KEYBOARD_LABEL = "Virtual Keyboard"

RESERVED_LABELS = {
    CLOSE_APP_LABEL,
    VIRTUAL_KEYBOARD_LABEL,
}

MAX_COMBOS = 20

MAX_NAME_LENGTH = 20

COOLDOWN_SECONDS = 0.5


class KeyComboManager:


    def __init__(
        self,
        config,
        save_config_fn
    ):

        self.config = config

        self.save_config_fn = save_config_fn

        if "key_combos" not in self.config:

            self.config["key_combos"] = []

        self._cooldown_until = 0.0


    @property
    def combos(self):

        return self.config["key_combos"]


    def menu_items(self):

        return (

            [VIRTUAL_KEYBOARD_LABEL, CLOSE_APP_LABEL]

            +

            [entry["name"] for entry in self.combos]

        )


    def can_add(self):

        return len(self.combos) < MAX_COMBOS


    def add(
        self,
        name,
        keys
    ):

        name = name.strip()[:MAX_NAME_LENGTH]

        if not name or not keys:

            return False

        if name in RESERVED_LABELS:

            return False

        self.combos.append(
            {
                "name": name,
                "keys": keys
            }
        )

        self.save_config_fn(
            self.config
        )

        return True


    def remove(
        self,
        name
    ):

        self.config["key_combos"] = [

            entry
            for entry in self.combos
            if entry["name"] != name

        ]

        self.save_config_fn(
            self.config
        )


    def keys_for(
        self,
        name
    ):

        for entry in self.combos:

            if entry["name"] == name:

                return entry["keys"]

        return None


    def in_cooldown(self):

        return time.time() < self._cooldown_until


    def run(
        self,
        name
    ):

        if self.in_cooldown():

            return False

        keys = self.keys_for(name)

        if not keys:

            return False

        try:

            keyboard.send(
                "+".join(keys)
            )

        except Exception:

            pass

        self._cooldown_until = time.time() + COOLDOWN_SECONDS

        return True
