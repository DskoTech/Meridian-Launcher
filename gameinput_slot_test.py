"""
Meridian GameInput Slot Tester
================================

A standalone diagnostic tool, run INSTEAD of Meridian Launcher, that
exhaustively tests IGameInputReading vtable slots 1 through 40 looking
for the one that actually returns GetGamepadState-shaped data with real
analog movement - the goal is to produce a log you can hand back so the
correct slot can be picked with certainty, instead of guessing.

WHY A SEPARATE SUPERVISOR/CHILD PROCESS DESIGN
-----------------------------------------------
Calling the wrong vtable slot can produce a genuine access violation - a
real CPU-level crash that no amount of Python try/except can catch,
because it isn't a Python exception, it's the OS terminating the process.
So each slot is tested in its own DISPOSABLE CHILD PROCESS:

  - This script, run with no arguments, is the SUPERVISOR. It launches
    itself again as a child process for each slot number, one at a time,
    and watches whether that child exits normally or dies abnormally.
  - Run with --child-slot=N, this script IS the child: it sets up
    GameInput, calls slot N the same way the real app would, and prompts
    YOU to move a stick or press a button within 5 seconds. If nothing
    happens in 5 seconds, that's recorded as "no input" (not a crash) and
    the child exits normally - the supervisor moves on to the next slot.
  - If a child crashes, the SUPERVISOR's own process is completely
    unaffected (it's just watching a subprocess), so it records that slot
    as CRASHED/SKIPPED and immediately continues with the next slot - no
    actual OS reboot needed, just a fresh child process.
  - Progress is saved to gameinput_slot_test_progress.json after every
    single slot, so if the supervisor itself is ever killed (e.g. you
    close the console), running this script again resumes right where it
    left off instead of re-testing slots you already have results for.

At the end (or any time you stop it), gameinput_slot_test_log.txt has a
full human-readable summary of every slot: crashed, no input seen, or the
raw decoded values for whichever button/axis actually changed - hand that
whole file back and the correct slot can be picked directly from it.

USAGE
-----
    python gameinput_slot_test.py

Just run it and follow the on-screen prompts - press buttons and move
both sticks and both triggers when it asks you to, for each slot in turn.
It's slow on purpose (up to 40 slots x up to 5 seconds each) so take your
time; you can stop it any time with Ctrl+C and re-run later to resume.
"""

import ctypes
import json
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
PROGRESS_FILE = os.path.join(HERE, "gameinput_slot_test_progress.json")
LOG_FILE = os.path.join(HERE, "gameinput_slot_test_log.txt")
CHILD_RESULT_FILE = os.path.join(HERE, "gameinput_slot_test_child_result.json")

FIRST_SLOT = 1
LAST_SLOT = 40
INPUT_WAIT_SECONDS = 5.0
POLL_INTERVAL = 0.05

# Exit codes the CHILD uses to tell the supervisor what happened, on top
# of "crashed" (which shows up as a nonzero/abnormal OS-level exit the
# child itself never gets to control).
EXIT_OK_SAW_INPUT = 0
EXIT_OK_NO_INPUT = 0        # same as above; the JSON result file has the detail
EXIT_SETUP_FAILED = 2       # GameInputCreate/QueryInterface itself failed - not this slot's fault


# ---------------------------------------------------------------------------
# Shared GameInput setup (confirmed-correct IID/GetCurrentReading slot; only
# the FINAL GetGamepadState-style call uses the slot under test)
# ---------------------------------------------------------------------------

class _GUID(ctypes.Structure):
    _fields_ = [
        ("Data1", ctypes.c_ulong), ("Data2", ctypes.c_ushort), ("Data3", ctypes.c_ushort),
        ("Data4", ctypes.c_ubyte * 8),
    ]

    @classmethod
    def from_string(cls, s):
        s = s.strip("{}")
        parts = s.split("-")
        data1 = int(parts[0], 16)
        data2 = int(parts[1], 16)
        data3 = int(parts[2], 16)
        data4_hi = bytes.fromhex(parts[3])
        data4_lo = bytes.fromhex(parts[4])
        data4 = data4_hi + data4_lo
        return cls(data1, data2, data3, (ctypes.c_ubyte * 8)(*data4))


IID_IGAMEINPUT = "11BE2A7E-4254-445A-9C09-FFC40F006918"

GAMEINPUT_KIND_GAMEPAD = 0x00000010


class _TestGamepadState(ctypes.Structure):
    """The shape we ask each candidate slot to fill, matching the real
    documented GamepadState layout (buttons + 2 triggers + 4 stick axes,
    all as the types GameInput.h declares)."""
    _fields_ = [
        ("buttons", ctypes.c_uint32),
        ("leftTrigger", ctypes.c_float),
        ("rightTrigger", ctypes.c_float),
        ("leftThumbstickX", ctypes.c_float),
        ("leftThumbstickY", ctypes.c_float),
        ("rightThumbstickX", ctypes.c_float),
        ("rightThumbstickY", ctypes.c_float),
    ]


def _com_method(obj_ptr, slot, restype, *argtypes):
    vtbl = ctypes.cast(obj_ptr, ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p))).contents
    proto = ctypes.WINFUNCTYPE(restype, ctypes.c_void_p, *argtypes)
    return proto(vtbl[slot])


def _setup_gameinput():
    """Returns (gameinput_ptr, get_current_reading_fn) or raises."""
    dll = ctypes.windll.gameinput
    create = dll.GameInputCreate
    create.argtypes = [ctypes.POINTER(ctypes.c_void_p)]
    create.restype = ctypes.c_long
    raw = ctypes.c_void_p()
    hr = create(ctypes.byref(raw))
    if hr != 0 or not raw:
        raise RuntimeError("GameInputCreate failed: HRESULT=0x%08X" % (hr & 0xFFFFFFFF))

    qi = _com_method(raw, 0, ctypes.c_long, ctypes.POINTER(_GUID), ctypes.POINTER(ctypes.c_void_p))
    iid = _GUID.from_string(IID_IGAMEINPUT)
    gi = ctypes.c_void_p()
    if qi(raw, ctypes.byref(iid), ctypes.byref(gi)) != 0 or not gi.value:
        raise RuntimeError("QueryInterface for IGameInput failed")
    _com_method(raw, 2, ctypes.c_ulong)(raw)  # release the GameInputCreate ref

    get_current_reading = _com_method(
        gi, 4, ctypes.c_long,
        ctypes.c_uint32, ctypes.c_void_p, ctypes.POINTER(ctypes.c_void_p),
    )
    return gi, get_current_reading


# ---------------------------------------------------------------------------
# Child: test exactly one slot
# ---------------------------------------------------------------------------

def _run_child(slot):
    print("=" * 70)
    print(f"[child] Testing IGameInputReading vtable slot {slot}")
    print("=" * 70)

    result = {"slot": slot, "setup_ok": False, "saw_input": False, "detail": "", "raw_samples": []}

    try:
        gi, get_current_reading = _setup_gameinput()
    except Exception as e:
        result["detail"] = f"GameInput setup failed (not this slot's fault): {e}"
        print(result["detail"])
        _write_child_result(result)
        sys.exit(EXIT_SETUP_FAILED)

    result["setup_ok"] = True
    print(f"[child] GameInput ready. Move BOTH sticks, pull BOTH triggers, and press")
    print(f"[child] some buttons now - you have {INPUT_WAIT_SECONDS:.0f} seconds...")
    sys.stdout.flush()

    deadline = time.time() + INPUT_WAIT_SECONDS
    reading_ptr = ctypes.c_void_p()
    saw_input = False
    samples_logged = 0

    while time.time() < deadline:
        hr = get_current_reading(gi, GAMEINPUT_KIND_GAMEPAD, None, ctypes.byref(reading_ptr))
        if hr == 0 and reading_ptr.value:
            state = _TestGamepadState()
            # THIS is the call under test - calling the candidate slot as
            # if it were GetGamepadState(IGameInputGamepadState*).
            get_state = _com_method(reading_ptr, slot, ctypes.c_bool, ctypes.POINTER(_TestGamepadState))
            ok = get_state(reading_ptr, ctypes.byref(state))
            # release the reading (slot 2 = Release, standard IUnknown)
            _com_method(reading_ptr, 2, ctypes.c_ulong)(reading_ptr)

            if ok:
                moved = (
                    abs(state.leftThumbstickX) > 0.25 or abs(state.leftThumbstickY) > 0.25 or
                    abs(state.rightThumbstickX) > 0.25 or abs(state.rightThumbstickY) > 0.25 or
                    state.leftTrigger > 0.2 or state.rightTrigger > 0.2 or
                    state.buttons != 0
                )
                if moved and samples_logged < 5:
                    line = (f"  buttons=0x{state.buttons:04X} LT={state.leftTrigger:.2f} "
                            f"RT={state.rightTrigger:.2f} LX={state.leftThumbstickX:.2f} "
                            f"LY={state.leftThumbstickY:.2f} RX={state.rightThumbstickX:.2f} "
                            f"RY={state.rightThumbstickY:.2f}")
                    print(line)
                    result["raw_samples"].append(line.strip())
                    samples_logged += 1
                if moved:
                    saw_input = True
        time.sleep(POLL_INTERVAL)

    result["saw_input"] = saw_input
    result["detail"] = "Saw real input on this slot." if saw_input else "No input detected (assumed none given) within timeout."
    print(f"[child] {result['detail']}")
    _write_child_result(result)
    sys.exit(EXIT_OK_SAW_INPUT if saw_input else EXIT_OK_NO_INPUT)


def _write_child_result(result):
    try:
        with open(CHILD_RESULT_FILE, "w", encoding="utf-8") as f:
            json.dump(result, f)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Supervisor: launch a fresh child per slot, watch for crashes
# ---------------------------------------------------------------------------

def _load_progress():
    if os.path.isfile(PROGRESS_FILE):
        try:
            with open(PROGRESS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"results": {}}  # slot(str) -> {"status": ..., "detail": ..., "raw_samples": [...]}


def _save_progress(progress):
    with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
        json.dump(progress, f, indent=2)


def _write_log(progress):
    lines = []
    lines.append("Meridian GameInput Slot Tester - results log")
    lines.append("=" * 70)
    lines.append("")
    crashed, no_input, saw_input, setup_failed = [], [], [], []
    for slot in range(FIRST_SLOT, LAST_SLOT + 1):
        r = progress["results"].get(str(slot))
        if r is None:
            continue
        status = r["status"]
        if status == "crashed":
            crashed.append(slot)
        elif status == "setup_failed":
            setup_failed.append(slot)
        elif status == "saw_input":
            saw_input.append(slot)
        else:
            no_input.append(slot)

    lines.append(f"Slots that CRASHED (blacklist these, never call them): {crashed or 'none'}")
    lines.append(f"Slots where GameInput setup itself failed (inconclusive): {setup_failed or 'none'}")
    lines.append(f"Slots with NO input detected in 5s: {no_input or 'none'}")
    lines.append(f"Slots that SAW REAL INPUT (these are the candidates!): {saw_input or 'none'}")
    lines.append("")
    lines.append("-" * 70)
    lines.append("Full detail per slot:")
    lines.append("-" * 70)
    for slot in range(FIRST_SLOT, LAST_SLOT + 1):
        r = progress["results"].get(str(slot))
        if r is None:
            lines.append(f"slot {slot:2d}: (not tested yet)")
            continue
        lines.append(f"slot {slot:2d}: {r['status'].upper()} - {r.get('detail', '')}")
        for sample in r.get("raw_samples", []):
            lines.append(f"           {sample}")
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def _run_supervisor():
    progress = _load_progress()
    print(__doc__)
    print()
    print(f"Testing slots {FIRST_SLOT}-{LAST_SLOT}. Progress file: {PROGRESS_FILE}")
    print(f"Log will be written to: {LOG_FILE}")
    print("Press Ctrl+C at any time to stop - progress is saved after every slot.")
    print()

    for slot in range(FIRST_SLOT, LAST_SLOT + 1):
        if str(slot) in progress["results"]:
            print(f"[supervisor] slot {slot}: already tested ({progress['results'][str(slot)]['status']}), skipping.")
            continue

        print()
        print(f"[supervisor] Launching child to test slot {slot}...")
        if os.path.isfile(CHILD_RESULT_FILE):
            try:
                os.remove(CHILD_RESULT_FILE)
            except Exception:
                pass

        try:
            proc = subprocess.Popen(
                [sys.executable, os.path.abspath(__file__), f"--child-slot={slot}"],
                cwd=HERE,
            )
            # A bit more than INPUT_WAIT_SECONDS for GameInput setup itself.
            proc.wait(timeout=INPUT_WAIT_SECONDS + 15)
            crashed = proc.returncode not in (EXIT_OK_SAW_INPUT, EXIT_OK_NO_INPUT, EXIT_SETUP_FAILED)
        except subprocess.TimeoutExpired:
            proc.kill()
            crashed = True
            print(f"[supervisor] slot {slot}: child hung and was killed - treating as crashed.")

        if crashed:
            progress["results"][str(slot)] = {
                "status": "crashed",
                "detail": f"Child process exited abnormally (return code {getattr(proc, 'returncode', '?')}) "
                          f"or hung - this slot is unsafe, never call it.",
                "raw_samples": [],
            }
            print(f"[supervisor] slot {slot}: CRASHED. Recorded and moving on.")
        else:
            child_result = None
            if os.path.isfile(CHILD_RESULT_FILE):
                try:
                    with open(CHILD_RESULT_FILE, "r", encoding="utf-8") as f:
                        child_result = json.load(f)
                except Exception:
                    child_result = None
            if child_result is None:
                progress["results"][str(slot)] = {
                    "status": "crashed",
                    "detail": "Child exited 'cleanly' but never wrote a result file - treating as unsafe.",
                    "raw_samples": [],
                }
            elif not child_result.get("setup_ok"):
                progress["results"][str(slot)] = {
                    "status": "setup_failed",
                    "detail": child_result.get("detail", ""),
                    "raw_samples": [],
                }
            else:
                progress["results"][str(slot)] = {
                    "status": "saw_input" if child_result.get("saw_input") else "no_input",
                    "detail": child_result.get("detail", ""),
                    "raw_samples": child_result.get("raw_samples", []),
                }

        _save_progress(progress)
        _write_log(progress)

    print()
    print("=" * 70)
    print("All done (or stopped). Log written to:")
    print(f"  {LOG_FILE}")
    print("Send that whole file back so the correct slot can be picked with certainty.")
    print("=" * 70)


def main():
    child_slot = None
    for arg in sys.argv[1:]:
        if arg.startswith("--child-slot="):
            child_slot = int(arg[len("--child-slot="):])

    if child_slot is not None:
        _run_child(child_slot)
    else:
        try:
            _run_supervisor()
        except KeyboardInterrupt:
            print()
            print("Stopped. Re-run this script any time to resume from where you left off.")


if __name__ == "__main__":
    main()
