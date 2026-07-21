"""gameinput_native/build_and_deploy.py — builds gameinput_native.pyd
and copies it next to every gameinput_api.py in the suite, in one step.

WHY THIS EXISTS
-----------------
setup.py's own instructions ("build it, then copy the .pyd next to
gameinput_api.py in every app folder that should use it") are a real,
easy-to-forget manual step - there are 7 copies of gameinput_api.py in
this repo (repo root + CyberDeckBrowser, Meridian Game Library,
Meridian_Explorer, Meridian_FileBrowse, Meridian_NetBrowse,
onscreenmenu), and gameinput_api.py's own factory function
(GameInputGamepad() in gameinput_api.py) silently and successfully falls
back to the old ctypes implementation in any folder that's missing its
copy - so a partial/forgotten deployment doesn't error, it just quietly
under-performs in whichever folders got missed, which is a genuinely
hard thing to notice without checking Settings > Controls' diagnostics
panel (DIAG["native_status"]) in each app individually.

This script does the whole thing in one call: builds the extension in
place, then copies the resulting .pyd to every one of those folders,
and finally prints a per-folder status line so a partial deployment
(e.g. one folder locked by a running process, and so unwritable) is
impossible to miss.

USAGE (from this folder, gameinput_native/):
    pip install pybind11 --break-system-packages
    python build_and_deploy.py
"""

import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parent

# Every folder with its own gameinput_api.py that should get the built
# .pyd - kept as an explicit list rather than "search for
# gameinput_api.py" so adding a new app folder to the suite is a
# deliberate one-line addition here, not something that silently starts
# or stops happening based on file layout alone.
DEPLOY_TARGETS = [
    REPO_ROOT,
    REPO_ROOT / "CyberDeckBrowser",
    REPO_ROOT / "Meridian Game Library",
    REPO_ROOT / "Meridian_Explorer",
    REPO_ROOT / "Meridian_FileBrowse",
    REPO_ROOT / "Meridian_NetBrowse",
    REPO_ROOT / "onscreenmenu",
]


def build():
    if sys.platform != "win32":
        sys.exit(
            "gameinput_native can only be built on Windows - GameInput is a "
            "Windows-only API (see gameinput_native.cpp's module docstring)."
        )
    print("Building gameinput_native.pyd ...")
    result = subprocess.run(
        [sys.executable, "setup.py", "build_ext", "--inplace"],
        cwd=str(HERE),
    )
    if result.returncode != 0:
        sys.exit("Build failed (see the compiler output above) - nothing was deployed.")


def find_built_pyd():
    # build_ext --inplace drops it right in this folder, named with the
    # Python/platform ABI tag (e.g. gameinput_native.cp312-win_amd64.pyd)
    # - matched by prefix+suffix rather than hardcoding the tag, since
    # that tag changes with the Python version doing the building.
    candidates = sorted(HERE.glob("gameinput_native*.pyd"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not candidates:
        sys.exit(
            "Build seemed to succeed but no gameinput_native*.pyd showed up in "
            + str(HERE) + " - nothing to deploy."
        )
    return candidates[0]


def deploy(pyd_path):
    print(f"\nDeploying {pyd_path.name} to every app folder:")
    any_failed = False
    for folder in DEPLOY_TARGETS:
        dest = folder / pyd_path.name
        try:
            folder.mkdir(parents=True, exist_ok=True)
            shutil.copy2(pyd_path, dest)
            print(f"  OK   {dest}")
        except Exception as e:
            any_failed = True
            print(f"  FAIL {dest} - {e}")
    if any_failed:
        print(
            "\nOne or more folders above failed to update - likely locked because "
            "that app is currently running. Close it and re-run this script; a "
            "partial deployment leaves those specific folders silently using the "
            "older ctypes fallback (check Settings > Controls there to confirm)."
        )
    else:
        print("\nAll folders updated.")


if __name__ == "__main__":
    build()
    deploy(find_built_pyd())
