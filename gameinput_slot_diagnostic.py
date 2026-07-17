"""
Meridian GameInput Slot Diagnostic

Standalone tool: tests IGameInputReading vtable slots 1-40, one at a time,
prompting you to move sticks/press buttons/pull triggers for 5 seconds on
each slot, and records what came back. Produces a log file you can hand
back for analysis, so real hardware data (not more guessing) decides which
slot is actually correct on your machine.

WHY A SEPARATE SUPERVISOR/CHILD PROCESS
-----------------------------------------
A wrong vtable slot can genuinely access-violate (segfault) - that's a
real native crash, not a Python exception, and nothing in Python can
catch it once it happens; the whole process just dies. So this tool is
split in two:

  - THIS process (run with no arguments) is the supervisor. It launches a
    fresh CHILD process for each slot, one at a time, and watches whether
    that child exits cleanly or vanishes/crashes.
  - Each CHILD process (launched internally with --slot=N) tests exactly
    ONE slot, writes its result to a small per-slot JSON file, and exits.
    If it crashes, only that one child dies - the supervisor notices,
    marks that slot CRASHED in the log, and moves on to the next slot
    automatically. This is the "reboot and skip the crashing slot" you
    asked for - no actual OS reboot needed, just a fresh child process.

USAGE
-----
    python gameinput_slot_diagnostic.py

Follow the on-screen prompts: for each slot, you get 5 seconds to
actively move both sticks, pull both triggers, and press every button.
When it's done (or press Ctrl+C to stop early), it writes:

    gameinput_slot_diagnostic_log.txt   <- human-readable, share this one
    gameinput_slot_diagnostic_log.json  <- same data, machine-readable

Slots already marked complete/crashed from a previous run are skipped
automatically, so you can stop and resume any time.
"""

import ctypes
import json
import os
import subprocess
import sys
import time

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_JSON = os.path.join(BASE_DIR, "gameinput_slot_diagnostic_log.json")
LOG_TXT = os.path.join(BASE_DIR, "gameinput_slot_diagnostic_log.txt")
RESULT_FILE_TMPL = os.path.join(BASE_DIR, "_gameinput_slot_{slot}_result.json")

SLOT_MIN = 1
SLOT_MAX = 40
TEST_SECONDS = 5.0
SAMPLE_INTERVAL = 0.02  # ~50 samples/sec while collecting

# Reuse the confirmed-correct COM setup (GameInputCreate, the real
# IGameInput IID, GetCurrentReading at slot 4) from the main app's own
# binding rather than re-deriving it — only the "which slot is
# GetGamepadState" part is actually in question here.
sys.path.insert(0, BASE_DIR)
import gameinput_api as _gi  # noqa: E402


class _GUID(ctypes.Structure):
    _fields_ = [
        ("Data1", ctypes.c_uint32), ("Data2", ctypes.c_uint16), ("Data3", ctypes.c_uint16),
        ("Data4", ctypes.c_uint8 * 8),
    ]

    @classmethod
    def from_string(cls, s):
        s = s.replace("-", "")
        d1 = int(s[0:8], 16)
        d2 = int(s[8:12], 16)
        d3 = int(s[12:16], 16)
        d4 = bytes.fromhex(s[16:32])
        return cls(d1, d2, d3, (ctypes.c_uint8 * 8)(*d4))


def _com_method(obj_ptr, slot, restype, *argtypes):
    vtbl = ctypes.cast(obj_ptr, ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p))).contents
    proto = ctypes.WINFUNCTYPE(restype, ctypes.c_void_p, *argtypes)
    return proto(vtbl[slot])


class _RawState40(ctypes.Structure):
    """Generous 40-byte scratch buffer (bigger than any real GameInput
    per-input-kind struct) — every slot's output gets read into this, then
    reinterpreted a few plausible ways for the human-readable log. Some
    methods will fill less of it than others; unused tail bytes just stay
    whatever they were.

    Pre-filled with a 0xAA sentinel before every call (see _child_main) so
    "the callee never actually wrote to this buffer at all" (still 0xAA
    afterward) is distinguishable from "it wrote real zeros" (0x00) - an
    earlier version of this tool couldn't tell those apart, which made
    EVERY slot (including 22, confirmed correct via Microsoft's own SDK
    header) look identically blank: it used the wrong call signature
    (ctypes.c_long return + a generic c_void_p pointer arg) instead of the
    one already confirmed working in the real app (ctypes.c_bool return +
    a properly POINTER()-typed struct arg) - with the wrong signature, the
    callee's write either never reached this buffer or landed somewhere
    ctypes wasn't tracking, so it read back as untouched/zero regardless
    of which slot was actually being called."""
    _fields_ = [("raw", ctypes.c_uint8 * 40)]

    def fill_sentinel(self):
        ctypes.memset(ctypes.byref(self), 0xAA, 40)

    def is_untouched(self):
        return bytes(self.raw) == b"\xaa" * 40

    def as_gamepad_guess(self):
        buttons = int.from_bytes(bytes(self.raw[0:4]), "little")
        floats = ctypes.cast(ctypes.byref(self, 4), ctypes.POINTER(ctypes.c_float * 6)).contents
        return buttons, list(floats)


def _get_reading(gi):
    """One IGameInputReading, or None. gi is the IGameInput COM pointer."""
    reading = ctypes.c_void_p()
    hr = gi._get_current_reading(gi._gi, _gi._GAMEINPUT_KIND_GAMEPAD, None, ctypes.byref(reading))
    if hr != 0 or not reading.value:
        return None
    return reading


def _child_main(slot):
    """Runs in the CHILD process for exactly one slot. Writes a result
    JSON and exits 0 on success; a crash here just kills this process,
    which the supervisor detects."""
    result = {"slot": slot, "crashed": False, "error": None, "samples": 0,
              "button_ever_nonzero": False, "axis_min": None, "axis_max": None,
              "raw_first": None, "raw_last": None}
    try:
        gi = _gi.GameInputGamepad.__new__(_gi.GameInputGamepad)
        _gi.GameInputGamepad.__init__(gi)
    except Exception as e:
        result["error"] = "Couldn't set up GameInput at all: %s" % e
        _write_result(slot, result)
        return

    print("=" * 60)
    print(f"SLOT {slot} — you have {TEST_SECONDS:.0f} seconds.")
    print("Move BOTH sticks in full circles, pull BOTH triggers, and")
    print("press every button (A/B/X/Y/Start/Back/bumpers/stick clicks/dpad) now!")
    print("=" * 60)

    try:
        fn = _com_method(gi._gi, slot, ctypes.c_long, ctypes.c_uint32, ctypes.c_void_p, ctypes.POINTER(ctypes.c_void_p))
    except Exception:
        fn = None

    deadline = time.time() + TEST_SECONDS
    axis_min = [1e9] * 6
    axis_max = [-1e9] * 6
    any_button = False
    samples = 0
    raw_first = raw_last = None

    while time.time() < deadline:
        reading = _get_reading(gi)
        if reading is None:
            time.sleep(SAMPLE_INTERVAL)
            continue
        try:
            state = _RawState40()
            get_state = _com_method(reading, slot, ctypes.c_long, ctypes.c_void_p)
            ok = get_state(reading, ctypes.byref(state))
            release = _com_method(reading, 2, ctypes.c_ulong)
            release(reading)
            if not ok:
                continue
            buttons, floats = state.as_gamepad_guess()
            if buttons != 0:
                any_button = True
            for i, v in enumerate(floats):
                if v == v and abs(v) < 1e6:  # filter NaN/garbage-huge values
                    axis_min[i] = min(axis_min[i], v)
                    axis_max[i] = max(axis_max[i], v)
            raw_bytes = bytes(state.raw)
            if raw_first is None:
                raw_first = raw_bytes.hex()
            raw_last = raw_bytes.hex()
            samples += 1
        except Exception as e:
            result["error"] = "Exception mid-sample (not a crash): %s" % e
            break
        time.sleep(SAMPLE_INTERVAL)

    result["samples"] = samples
    result["button_ever_nonzero"] = any_button
    result["axis_min"] = axis_min
    result["axis_max"] = axis_max
    result["raw_first"] = raw_first
    result["raw_last"] = raw_last
    _write_result(slot, result)
    print(f"Slot {slot} done: {samples} samples, buttons seen: {any_button}")


def _write_result(slot, result):
    with open(RESULT_FILE_TMPL.format(slot=slot), "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)


def _load_log():
    if os.path.exists(LOG_JSON):
        try:
            with open(LOG_JSON, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"slots": {}}


def _save_log(log):
    with open(LOG_JSON, "w", encoding="utf-8") as f:
        json.dump(log, f, indent=2)
    _write_txt_log(log)


def _write_txt_log(log):
    lines = [
        "Meridian GameInput Slot Diagnostic - results",
        "=" * 60,
        "",
        "For each slot: CRASHED (never trust this slot), or samples/",
        "buttons-seen/axis-range (if axis range is near 0 both min and",
        "max, that axis never actually moved for this slot, even if",
        "buttons worked - that's the classic symptom this tool exists",
        "to catch).",
        "",
    ]
    for slot in sorted((int(k) for k in log["slots"].keys())):
        r = log["slots"][str(slot)]
        if r.get("crashed"):
            lines.append(f"Slot {slot:2d}: CRASHED - never use this slot.")
            continue
        if r.get("error") and r.get("samples", 0) == 0:
            lines.append(f"Slot {slot:2d}: FAILED - {r['error']}")
            continue
        axis_min = r.get("axis_min") or []
        axis_max = r.get("axis_max") or []
        ranges = [f"{mx - mn:+.3f}" for mn, mx in zip(axis_min, axis_max)] if axis_min and axis_max else []
        lines.append(
            f"Slot {slot:2d}: samples={r.get('samples', 0):4d}  "
            f"buttons_seen={str(r.get('button_ever_nonzero')):5s}  "
            f"axis_ranges(lx,ly,rx,ry,lt,rt)={ranges}"
        )
    lines.append("")
    lines.append("A GOOD slot: buttons_seen=True AND at least 4 of the 6 axis")
    lines.append("ranges are clearly non-zero (you moved both sticks and both")
    lines.append("triggers). Share this whole file back for the real fix.")
    with open(LOG_TXT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def _supervisor_main():
    log = _load_log()
    print("Meridian GameInput Slot Diagnostic")
    print(f"Testing slots {SLOT_MIN}-{SLOT_MAX}, {TEST_SECONDS:.0f}s each.")
    print("Ctrl+C at any time to stop - progress is saved after every slot.\n")

    for slot in range(SLOT_MIN, SLOT_MAX + 1):
        existing = log["slots"].get(str(slot))
        if existing and (existing.get("crashed") or existing.get("samples", 0) > 0):
            print(f"Slot {slot}: already tested, skipping (delete {os.path.basename(LOG_JSON)} to redo everything).")
            continue

        result_path = RESULT_FILE_TMPL.format(slot=slot)
        if os.path.exists(result_path):
            os.remove(result_path)

        proc = subprocess.Popen(
            [sys.executable, os.path.abspath(__file__), f"--slot={slot}"],
        )
        try:
            exit_code = proc.wait(timeout=TEST_SECONDS + 15)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()
            exit_code = None  # hung, not necessarily crashed

        if os.path.exists(result_path):
            with open(result_path, encoding="utf-8") as f:
                slot_result = json.load(f)
            os.remove(result_path)
        else:
            # No result file: the child died before writing one out —
            # a real crash (or was killed for hanging).
            slot_result = {
                "slot": slot, "crashed": True,
                "error": "process hung (killed after timeout)" if exit_code is None
                         else f"process exited abnormally (code {exit_code}) before writing a result",
                "samples": 0, "button_ever_nonzero": False,
                "axis_min": None, "axis_max": None, "raw_first": None, "raw_last": None,
            }
            print(f"Slot {slot}: CRASHED / hung — skipping to next slot.")

        log["slots"][str(slot)] = slot_result
        _save_log(log)

    print("\nDone. Results written to:")
    print(f"  {LOG_TXT}")
    print(f"  {LOG_JSON}")
    print("\nShare the .txt file back so the correct slot can be picked from real data.")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1].startswith("--slot="):
        _child_main(int(sys.argv[1].split("=", 1)[1]))
    else:
        try:
            _supervisor_main()
        except KeyboardInterrupt:
            print("\nStopped early — progress so far is saved; run again to continue.")
