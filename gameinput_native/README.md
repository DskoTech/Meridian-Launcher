# gameinput_native

A small pybind11 C++ extension that wraps Microsoft's real GameInput SDK
for gamepad state, replacing the old ctypes vtable-slot-guessing
implementation in `gameinput_api.py`'s `GameInputGamepad` class.

## Why this exists

The previous implementation didn't have real GameInput headers to build
against, so it read `gameinput.dll` via raw ctypes vtable-slot indices it
had to *guess* — starting from slot 23, falling back through 22/24/21/25,
with a whole "probation" mechanism (see `gameinput_api.py`'s docstring
history) to avoid trusting a wrong slot's garbage memory. It never
reliably worked.

With the real SDK (Microsoft's public NuGet package, vendored here under
`vendor/GameInput/`), none of that guessing is necessary:

- The real `IID_IGameInput` is
  `20EFC1C7-5D9A-43BA-B26F-B807FA48609C` — **not** the value the old code
  had, which explains a lot.
- `IGameInputReading::GetGamepadState` sits at real vtable slot **18**
  (3 `IUnknown` methods + 15 `IGameInputReading` methods ahead of it),
  not the 22/23 the old code was trying.

The C++ compiler resolves all of this correctly from the real interface
declaration in `GameInput.h`; nothing in this extension is guessed.

## Building

Windows + MSVC only — GameInput is a Windows-only API.

**If GameInput "isn't working" and you're reading this because of that:**
the single most likely cause is simply that this extension has never
been compiled. A `.cpp` file sitting in the repo doesn't do anything by
itself — pybind11 extensions like this one need an actual Windows+MSVC
build step before Python can import them at all. Until that's done,
`gameinput_api.py` silently and successfully falls back to its older,
admittedly-unreliable ctypes implementation in every single app,
everywhere — no error, no crash, just quietly never using the real SDK.
Check **Settings > Controls** in any of the apps for
`DIAG["native_status"]`; it now always says exactly which of these is
true: not built, built but not deployed to this folder, deployed but
`gameinput.dll` itself isn't installed on this machine, or genuinely
active.

1. Install the MSVC Build Tools (Visual Studio Build Tools, "Desktop
   development with C++" workload) if you don't already have them.
2. `pip install pybind11 --break-system-packages`
3. From this folder: `python build_and_deploy.py`

This builds `gameinput_native.<platform tag>.pyd` and automatically
copies it to every app folder that needs one (repo root,
CyberDeckBrowser, Meridian Game Library, Meridian_Explorer,
Meridian_FileBrowse, Meridian_NetBrowse, onscreenmenu) in one step,
printing a per-folder OK/FAIL line so a partial deployment (e.g. one
app folder locked because it's currently running) can't go unnoticed.
Running `python setup.py build_ext --inplace` directly still works too
if you'd rather copy the .pyd around by hand - see "Distributing it"
below for why doing that manually is easy to get subtly wrong.

## Distributing it

Copy the built `.pyd` next to `gameinput_api.py` in every app folder that
should use it — same convention as `SDL3.dll`:

```
MeridianLauncher.exe
gameinput_native.cp312-win_amd64.pyd   <- next to the exe
...
```

`gameinput_api.py` imports it opportunistically at the top of the file;
if it's missing (not built yet, or you're on a non-Windows dev machine),
the old ctypes-based `GameInputGamepad` is still there as an automatic
fallback so nothing else breaks — but the native module is the correct,
authoritative implementation whenever it's present. One specific gotcha
this now actively detects rather than silently falling into: this
`gameinput_native/` *source* folder (this one - the .cpp/setup.py/
vendor/ folder, not a built .pyd) sits at the repo root right next to
the root copy of `gameinput_api.py`. Without a real compiled `.pyd`
there, `import gameinput_native` from that copy resolves to *this
folder itself* as an empty Python namespace package instead of raising
an ImportError - `gameinput_api.py` checks for exactly that case now
(no `GameInputPad` attribute, no `__file__`) and reports it plainly via
`DIAG["native_status"]` instead of it looking identical to "not built at
all."

## The runtime DLL

This extension links against `vendor/GameInput/lib/x64/GameInput.lib`
(the *import* library, used only at build/link time) — at runtime it
needs the actual `gameinput.dll` to be present on the system. Most
gaming-oriented Windows installs already have it (it ships with the
Xbox app / Game Bar and Windows' own Xbox integration), but it isn't
guaranteed on every machine.

`vendor/GameInput/redist/GameInputRedist.msi` (from the same SDK
download, not copied into this repo to keep it small — re-download from
https://github.com/microsoft/GDK/ or the NuGet package if you need it)
is Microsoft's official redistributable installer for it. If you want
`InstallMeridianSuite.bat` to install this automatically the way it
already does for the WebView2 Runtime and VC++ Redistributable, that
MSI is the thing to wire in — not currently done, since this extension
still needs to actually be built and tested on real hardware first.

## Testing

Compiles and runs on real hardware as of a real build/test round: it
loads, `GameInputCreate()` succeeds, and `poll()` returns real readings
(not `None`) at a steady rate. What's still being tracked down: a real
diagnostic dump showed thousands of successful readings with every
button/stick/trigger value permanently at zero, even during active
testing - `Poll()` now also returns the untranslated raw button bitmask
and the reading's timestamp specifically to narrow this down (see
`GameInputPad::Poll()`'s own comment for exactly what each new field
rules in or out: a wrong/phantom device via the null-device
aggregation this class uses, a frozen/stale reading that never
actually refreshes, or a bug in `TranslateButtons` itself). Rebuild,
retest, and check `gameinput_diag_dump_*.txt`'s `native_raw_buttons`/
`native_timestamp_changing` fields (or Settings > Controls' "Dump
Diagnostics Now" button) for the next data point.
