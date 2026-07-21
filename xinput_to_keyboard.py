"""Meridian Controller-to-Keyboard Bridge

Reads a real controller (via the same gameinput_api.py backend chain
every other Meridian app uses - XInput by default, with GameInput,
DirectInput, and SDL3 as fallbacks, including the PlayStation DualShock/
DualSense support built into that module) and emits KEYBOARD key
presses/releases matching a configurable mapping - i.e. it turns a real
controller into emulated keyboard input.

WHY THIS EXISTS
---------------
Plenty of emulators (older cores especially) and plain old PC games only
ever learned to read a keyboard, never a controller - RetroArch cores set
to keyboard-only input, DOS/early-Windows-era games, some browser-based
emulators, etc. Rather than needing a separate general-purpose remapper
tool (JoyToKey, AntiMicroX, etc) installed alongside the Meridian suite
just for that, this is a small, single-purpose bridge in the same style
and using the same input backend as everything else here - so it also
means any controller Meridian Launcher already supports (including a
PlayStation pad, thanks to gameinput_api.py's DirectInput/SDL3 handling)
works here too, with no separate setup.

USAGE
-----
    python xinput_to_keyboard.py                  # default mapping
    python xinput_to_keyboard.py --config my.json  # custom mapping
    python xinput_to_keyboard.py --list-mapping     # print the active mapping and exit
    python xinput_to_keyboard.py --backend sdl3     # force a specific input backend

Ctrl+C to stop. While running, it just sits in the background translating
button presses/stick tilts into key presses - it doesn't take over the
controller (XInput/GameInput/DirectInput/SDL3 all support multiple
simultaneous readers), so Meridian Launcher and this can both be reading
the same physical pad at once without conflict.

CONFIG FILE
-----------
A JSON object mapping button/axis names to keyboard key names (whatever
the `keyboard` library's send()/press()/release() accept - "a", "up",
"enter", "space", "f1", etc). Buttons not listed are simply never
translated (harmless - Meridian Launcher's own reading of the same pad
is completely unaffected by this tool either way).

Recognized button names (same as gameinput_api.XI_BUTTONS): A, B, X, Y,
LEFT_SHOULDER, RIGHT_SHOULDER, BACK, START, LEFT_THUMB, RIGHT_THUMB,
DPAD_UP, DPAD_DOWN, DPAD_LEFT, DPAD_RIGHT, GUIDE.

Recognized stick/trigger pseudo-buttons (digital: fires past a deadzone,
same as a button press/release, not an analog value): LSTICK_UP,
LSTICK_DOWN, LSTICK_LEFT, LSTICK_RIGHT, RSTICK_UP, RSTICK_DOWN,
RSTICK_LEFT, RSTICK_RIGHT, LEFT_TRIGGER, RIGHT_TRIGGER.

Example (see DEFAULT_MAPPING below for the built-in default, which this
would override/extend - a config file only needs to list what it wants
to CHANGE from that default; anything else keeps the default):

    {
      "A": "z", "B": "x", "X": "a", "Y": "s",
      "DPAD_UP": "up", "DPAD_DOWN": "down",
      "DPAD_LEFT": "left", "DPAD_RIGHT": "right",
      "START": "enter", "BACK": "esc"
    }

Pass "" (empty string) for a name to explicitly UN-map something the
default mapping sets, rather than leaving it at the default.
"""

import argparse
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gameinput_api  # noqa: E402

try:
    import keyboard
except ImportError:
    keyboard = None


# Sensible defaults matching common retro-emulator conventions (arrow
# keys for movement, Z/X for the two most-used face buttons, Enter/Esc
# for Start/Back) - a config file only needs to override what it wants
# different, per the module docstring above.
DEFAULT_MAPPING = {
    "DPAD_UP": "up", "DPAD_DOWN": "down", "DPAD_LEFT": "left", "DPAD_RIGHT": "right",
    "LSTICK_UP": "up", "LSTICK_DOWN": "down", "LSTICK_LEFT": "left", "LSTICK_RIGHT": "right",
    "A": "z", "B": "x", "X": "a", "Y": "s",
    "LEFT_SHOULDER": "q", "RIGHT_SHOULDER": "w",
    "LEFT_TRIGGER": "e", "RIGHT_TRIGGER": "r",
    "START": "enter", "BACK": "esc",
    # Everything else assignable gets a plain number key by default (1-9)
    # rather than being left unmapped - a real default a person can play
    # with immediately, that's still trivially easy to identify and
    # reassign in a per-game config (see PER_GAME_CONFIG_FILENAME below)
    # rather than guessing what an empty string used to mean.
    "LEFT_THUMB": "1", "RIGHT_THUMB": "2", "GUIDE": "3",
    "RSTICK_UP": "4", "RSTICK_DOWN": "5", "RSTICK_LEFT": "6", "RSTICK_RIGHT": "7",
}

STICK_DEADZONE = 0.5   # how far a stick has to tilt to count as "pressed"
TRIGGER_DEADZONE = 0.5  # how far a trigger has to pull to count as "pressed"
POLL_HZ = 125  # matches typical controller report rates; plenty responsive for keyboard emulation


# Dropping a JSON file with this exact name in a game's own install
# folder (its root - wherever the game's main .exe actually lives, not
# a save-data folder) is picked up automatically, with no need to
# browse-select a mapping file by hand for every game that needs one.
# Same override format as any other config file (see the module
# docstring) - only needs to list what it wants to CHANGE from
# DEFAULT_MAPPING above.
PER_GAME_CONFIG_FILENAME = "meridian_controller_bridge.json"


def load_mapping(config_path=None, game_dir=None):
    """Priority order: an explicit --config path always wins if given;
    otherwise a PER_GAME_CONFIG_FILENAME sitting in game_dir (the game's
    own folder) is used automatically if present; otherwise it's just
    DEFAULT_MAPPING as-is. Either source only needs to list what it
    wants to override - both are layered on top of DEFAULT_MAPPING, not
    a full replacement of it."""
    mapping = dict(DEFAULT_MAPPING)
    chosen_path = config_path
    if not chosen_path and game_dir:
        candidate = os.path.join(game_dir, PER_GAME_CONFIG_FILENAME)
        if os.path.isfile(candidate):
            chosen_path = candidate
    if chosen_path:
        with open(chosen_path, "r", encoding="utf-8") as f:
            overrides = json.load(f)
        mapping.update(overrides)
    return mapping


def digital_buttons_from_snapshot(snap):
    """Every XI_BUTTONS bit that's currently pressed, plus the
    stick/trigger pseudo-buttons this tool adds on top (see the
    module docstring) - all as one flat set of names, so the rest of
    this tool doesn't need to treat sticks/triggers any differently
    from real buttons."""
    pressed = {name for name, bit in gameinput_api.XI_BUTTONS.items() if snap.buttons & bit}
    if snap.ly > STICK_DEADZONE:
        pressed.add("LSTICK_UP")
    if snap.ly < -STICK_DEADZONE:
        pressed.add("LSTICK_DOWN")
    if snap.lx < -STICK_DEADZONE:
        pressed.add("LSTICK_LEFT")
    if snap.lx > STICK_DEADZONE:
        pressed.add("LSTICK_RIGHT")
    if snap.ry > STICK_DEADZONE:
        pressed.add("RSTICK_UP")
    if snap.ry < -STICK_DEADZONE:
        pressed.add("RSTICK_DOWN")
    if snap.rx < -STICK_DEADZONE:
        pressed.add("RSTICK_LEFT")
    if snap.rx > STICK_DEADZONE:
        pressed.add("RSTICK_RIGHT")
    if snap.lt > TRIGGER_DEADZONE:
        pressed.add("LEFT_TRIGGER")
    if snap.rt > TRIGGER_DEADZONE:
        pressed.add("RIGHT_TRIGGER")
    return pressed


def run(mapping, backend=None, log=print):
    if keyboard is None:
        log("The 'keyboard' package isn't installed - run: pip install keyboard --break-system-packages")
        return 1

    prefer = (backend,) if backend else None
    pad = gameinput_api.open_gamepad(prefer=prefer, log=log)
    if pad is None:
        log("No controller backend available on this system.")
        return 1
    log(f"Controller-to-Keyboard Bridge running (backend: {pad.backend}). Ctrl+C to stop.")

    active_mapping = {name: key for name, key in mapping.items() if key}  # drop "" (explicitly unmapped)
    prev_held = set()
    interval = 1.0 / POLL_HZ

    try:
        while True:
            snap = None
            try:
                snap = pad.poll()
            except Exception:
                snap = None

            held = digital_buttons_from_snapshot(snap) if snap is not None else set()

            # Press whatever's newly held, release whatever's no longer held -
            # only for names this mapping actually cares about, so an
            # unmapped button costs nothing here.
            for name in held - prev_held:
                key = active_mapping.get(name)
                if key:
                    try:
                        keyboard.press(key)
                    except Exception as e:
                        log(f"Couldn't press '{key}' for {name}: {e}")
            for name in prev_held - held:
                key = active_mapping.get(name)
                if key:
                    try:
                        keyboard.release(key)
                    except Exception as e:
                        log(f"Couldn't release '{key}' for {name}: {e}")

            prev_held = held
            time.sleep(interval)
    except KeyboardInterrupt:
        pass
    finally:
        # Don't leave any key stuck "held" on exit.
        for name in prev_held:
            key = active_mapping.get(name)
            if key:
                try:
                    keyboard.release(key)
                except Exception:
                    pass
        try:
            pad.close()
        except Exception:
            pass
    return 0


def main():
    parser = argparse.ArgumentParser(description="Bridge a real controller into emulated keyboard input.")
    parser.add_argument("--config", help="JSON file overriding DEFAULT_MAPPING (see this file's module docstring).")
    parser.add_argument("--game-dir",
                         help=f"A game's install folder to check for {PER_GAME_CONFIG_FILENAME} "
                              "automatically - ignored if --config is also given.")
    parser.add_argument("--backend", choices=["xinput", "gameinput", "directinput", "sdl3"],
                         help="Force one input backend instead of the usual auto-fallback chain.")
    parser.add_argument("--list-mapping", action="store_true", help="Print the active button->key mapping and exit.")
    args = parser.parse_args()

    mapping = load_mapping(args.config, args.game_dir)

    if args.list_mapping:
        for name, key in mapping.items():
            print(f"  {name:14s} -> {key or '(unmapped)'}")
        return 0

    return run(mapping, backend=args.backend)


if __name__ == "__main__":
    sys.exit(main())
