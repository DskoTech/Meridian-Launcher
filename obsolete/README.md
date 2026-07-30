# obsolete/

Files moved here are ones that appear to be superseded by later work
elsewhere in the suite, but were **not deleted** — only quarantined —
so you can review each one and decide whether to actually remove it or
pull it back into active use. Nothing in here is referenced by any
current build script, install script, or app code; moving this whole
folder away (or deleting it) should have zero effect on anything that
currently works.

## Meridian_NetBrowse_LegacyEngine/

The full original "Meridian NetBrowse" browser engine — `main.py`,
`launcher.py`, `browser/`, `controller/`, `cursor/`, `input/`,
`keyboard/`, `menus/`, `ui/`, `config.py`, `default_browser.py`,
`gameinput_api.py`, `paths.py`, `crash_logger.py`, and its own
`Requirements.txt`/`install requirements.bat`.

**Why it's here:** CyberDeckBrowser absorbed everything this app did,
via its own `--box=X,Y,W,H` argument (see
`CyberDeckBrowser/main.py`'s module docstring) — Meridian Launcher's
Browser section now launches `CyberDeckBrowser.exe` boxed instead of a
separate NetBrowse engine. Running two full separate QtWebEngine/
Chromium bundles side by side was a significant contributor to the
suite's total compiled size, and keeping the login-persistence /
streaming-codec fixes in sync across two copies of the same browser
code going forward would be pure duplicated maintenance for a feature
CyberDeckBrowser already covers.

**What's NOT here:** `Meridian_NetBrowse/netbrowse_shell_handler.py`
and `Meridian_NetBrowse/buildMeridianNetBrowse.bat` are still in their
original location — that's a small, fully self-contained trampoline
(stdlib only, no dependency on anything in this quarantined folder)
that Windows invokes as the registered default web browser, whose only
job is handing a URL to an already-running Meridian Launcher. It's
still genuinely used by the "Make Meridian NetBrowse the default
system web browser" setting, so it stays active. The build script was
trimmed to only build that trampoline — it used to also build the now-
quarantined full engine as "Meridian NetBrowse.exe".

**If you want it back:** move the folder's contents back into
`Meridian_NetBrowse/` and restore `buildMeridianNetBrowse.bat`'s
original full build step (or ask for it back — that's a mechanical
revert).

## GameInput_SlotGuessing_DiagnosticTools/

`gameinput_slot_test.py`, `gameinput_slot_diagnostic.py`, and
`RunGameInputSlotTest.bat` — standalone tools for empirically
determining the correct `IGameInputReading` vtable slot by testing
slots 1-40 against real hardware input, one at a time.

**Why it's here:** these exist entirely to work around not having
Microsoft's real GameInput SDK headers to build against — see
`gameinput_native/README.md` for the full story. Now that
`gameinput_native/` provides the real, compiler-resolved implementation
(no slot-guessing at all), these tools' entire purpose doesn't apply to
anyone using it. They're not *fully* dead, though: `gameinput_api.py`'s
old ctypes-based vtable-guessing implementation is still there as the
automatic fallback for machines where `gameinput_native.pyd` hasn't
been built (no MSVC Build Tools) — these tools would still have some
diagnostic value specifically for that fallback path, which is the
reason they're quarantined here rather than deleted outright.

**If you want them back:** move the three files back to the repo root.

## osk_osm_bat_files/

`osk.bat` (all copies), `osm.bat` (all copies), `MakeUnmakeShell.ps1`, and
`MeridianExplorerShellIntegration.bat`.

**Why they're here:** all four are now fully internalized directly in
Python, with every call site across the whole suite updated to call the
internalized equivalent instead of shelling out to these files:

- `osk.bat` (toggle the real Windows on-screen keyboard) → each app now
  does this directly via `tasklist`/`taskkill`/`os.startfile("osk.exe")`
  calls in Python (see `toggle_osk()` in onscreenmenu's `ui/main_window.py`,
  `run_osk()` in CyberDeckBrowser's `ui/main_window.py`, and `main.py`'s
  own osk-toggling Api methods).
- `osm.bat` (launch onscreenmenu.exe if it isn't already running) →
  `_launch_onscreenmenu()` in `main.py`, and equivalent functions in
  Meridian Explorer, Meridian FileBrowse, Meridian Game Library, and
  onscreenmenu itself.
- `MakeUnmakeShell.ps1` (toggle Meridian Launcher as the Windows shell)
  → `_toggle_default_shell()` in `main.py`, using `winreg` directly - as
  a bonus, this no longer needs the elevated-relaunch the PowerShell
  version implied, since the registry key involved is `HKEY_CURRENT_USER`
  and never needed admin rights in the first place.
- `MeridianExplorerShellIntegration.bat` → already fully superseded by
  `explorer_shell.py` (pure `winreg`, no external file at all) before
  this cleanup pass even started; nothing in the app was calling the
  `.bat` version anymore.

**If you want any of them back:** each is self-contained and still
fully functional as a standalone script - move it back to its original
location. Nothing else needs to change to keep using it that way.

