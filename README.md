# Meridian Launcher

A cross-bar style desktop front-end / app launcher for Windows: one
horizontal row of sections, a vertical list per section, navigable by
keyboard, mouse, or game controller.

**This build targets Windows only.** Most of its features — launching
.exe/.bat files, opening Explorer/Control Panel/Task Manager, shutdown/sleep/
hibernate, and XInput controller support — are Windows-specific, so there's
no meaningful cross-platform version of this particular feature set.


## Sections

- **Music / Photos / Videos** — point it at folders in Settings; it scans,
  shows thumbnails/album art, and plays back in-app.
- **Apps / Games / Emulators / Chat / Streaming** — add any `.exe` from
  Settings; shows up as a tile, click/confirm to launch.
- **Web** — launches your system default browser.
- **Files** — opens a native Windows Explorer window at "This PC".
- **System** — Shut Down, Sleep, Hibernate, Close Program, Control Panel,
  Task Manager.
- **Macros** — "All Other Programs" closes every other running app except
  a whitelist (see safety note below); you can also add your own `.bat`
  scripts here.
- **Custom sections** — from Settings, "+ Add custom section" opens a
  small dialog to name a new section; it behaves just like Apps/Games —
  add/remove `.exe`s from Settings.

Every launchable entry is shown by filename only — no path, no extension
(`C:\Program Files\Google\Chrome\chrome.exe` → `chrome`).

## Controls

- **Keyboard:** arrow keys navigate, default confirm is **Enter**, default
  back is **Space**, **Escape always quits** (not remappable — this is a
  hard rule per spec, separate from the confirm/back mapping).
- **Mouse:** click any category or item directly.
- **Controller (XInput):** D-pad or left stick to navigate, **A** to
  confirm, **B** to back out, **Start+Back together** brings the app to the
  foreground even if it's minimized or unfocused, **L3+R3 together** quits
  the app entirely.
- Stick input has a dead zone (default 0.25) and a 200 ms cooldown between
  repeated nav events, so sensitivity doesn't cause overshoot.

Two files are generated in the app's root folder on first run and are meant
to be hand-edited to remap controls:
- `keyboard_controls.json`
- `controller_controls.json` (also holds `deadzone` and `cooldown_ms`)

All your added apps/games/folders/sections live in `settings.json`, also in
the app's root folder.

## Appearance

From Settings you can set:
- A **custom background image**.
- A **custom overlay** (`overlay.png`, generated automatically when you pick
  one) — it's scaled to cover the screen, and **pure white pixels are made
  transparent**, so you can lay a frame/vignette/logo over the background.
  Toggle it on/off independently of having one assigned.
- An **opening video** that plays once, full screen, on launch, then closes
  into the main menu automatically. **Any key, mouse click, or controller
  button skips it immediately.**
- **Window mode**: Fullscreen / Windowed / Kiosk (kiosk = fullscreen,
  frameless; switching to/from kiosk takes effect on next launch since it
  changes how the window is created — Fullscreen/Windowed toggle instantly).
  Selecting Kiosk shows a confirmation prompt disclosing the three ways to
  turn it back off (see above); once on, Settings and System are hidden
  from the category row until it's disabled.
- The app auto-detects your screen resolution at boot and sizes itself to
  match.


## Safety note on "Macros -> All Other Programs"

This closes other running applications, but it will **never** touch core
Windows/session processes (`explorer.exe`, `dwm.exe`, `csrss.exe`,
`svchost.exe`, etc.) regardless of your whitelist — killing those crashes
the desktop rather than just closing programs. Meridian Launcher itself and
`onscreenmenu.exe` are always protected too. In practice this behaves as
"close all other user-facing apps," which is what a kiosk/arcade front-end
actually needs.

## Run it

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

Optional: install ffmpeg and put it on PATH for video thumbnails/durations.
Everything else still works without it.

## Building a standalone Windows .exe

**Easiest (Windows, no typing):** run `install_dependencies.bat` once, then
run `compile.bat`. Output lands in `dist\Meridian Launcher.exe`.

**GitHub Actions (no Windows machine needed):** push this repo to GitHub,
go to Actions -> "Build Windows executable" -> Run workflow (or push a tag
like `v0.1`), then download the `Meridian-Launcher-windows` artifact.

**Locally on Windows, by hand:**
```bash
pip install -r requirements.txt
pyinstaller meridian.spec
```
Output lands in `dist/Meridian Launcher.exe`.

The build is already wired to use `icon.ico` (in the project root) as the
compiled .exe's icon — shown in Explorer, the taskbar, and the window's
title bar/Alt-Tab thumbnail. Swap that file for your own `.ico` if you want
a different one; no other changes are needed, PyInstaller picks it up via
`icon='icon.ico'` in `meridian.spec`.

## Project layout

```
main.py                 backend: API, media server, window/controller setup
store.py                settings.json + controls JSON persistence
system_actions.py       shutdown/sleep/hibernate/explorer/taskmgr/close-others
controller_input.py     XInput polling, dead zones, cooldown, combos
frontend/
  index.html
  style.css
  app.js
meridian.spec           PyInstaller build config
icon.ico                app icon (16-256px), baked into the compiled .exe
install_dependencies.bat  installs Python deps, preps for a Windows build
compile.bat              runs PyInstaller to produce Meridian Launcher.exe
.github/workflows/      CI build for Windows
```

## Section-item icons

Apps/Games/Emulators/Chat/Streaming/custom-section tiles and Macro `.bat`
entries show the actual icon Windows would display for that file, pulled
via `ExtractIconEx` and cached as PNGs in `.cache/` alongside the media
thumbnails. If extraction fails for a given file (rare, but some odd file
types or icon formats can trip it up), it falls back to a generic icon for
that section instead of breaking anything. (This is separate from the
app's own icon — see `icon.ico` above.)

## style redesign (this revision)

Rebuilt the navigation model to match genuine Xross Media Bar behavior
instead of trying to patch the old one:

- **Categories moved to the top**, aligned with the clock, instead of
  floating in the vertical center.
- **No more separate "enter a section" step.** The category row is always
  live: moving Left/Right instantly shows that section's list underneath,
  the same way real XMB works. Up/Down always browses whatever list is
  currently shown; Left/Right always changes category, even while you're
  mid-list. Clicking a category or an item does the same thing a
  confirm-press would.
- **All section content is now a single-column list** (music, photos,
  videos, apps, games, etc. all render the same way — icon/thumbnail +
  title, one row per item) rather than a mix of grids and lists. This
  removes an entire class of ambiguity around what Left/Right should do
  inside a multi-column grid.
- **Empty sections no longer auto-redirect on mere browsing.** Casually
  scrolling past an empty Apps or Games section just shows an inline
  "nothing added yet" row in place — it won't yank you into Settings just
  because you passed over it. Only an explicit confirm on that row jumps
  into Settings, scrolled to and highlighting the right block.
- **System now sits after Settings, as the very last section**, and always
  shows its list of options (Task Manager, Control Panel, Close Program,
  Sleep, Hibernate, Shut Down) — selecting the System category itself never
  executes anything on its own. The list is also ordered safe-first, so a
  stray confirm lands on Task Manager, not Shut Down.
- **Confirm/Back/Escape now ignore OS key auto-repeat** (`e.repeat`).
  Previously, holding a key down (or a slightly slow release) could let a
  single keypress fire twice in a row — enter a section, then immediately
  "confirm" its first item on the auto-repeated event. That's the likely
  explanation for options ever appearing to execute immediately instead of
  showing a list. Only Up/Down/Left/Right (pure browsing) are still allowed
  to repeat, since holding those to scroll through a list is normal and
  expected. Controller confirm/back were already immune to this since
  XInput polling uses rising-edge detection, not raw button state.

Verified with a headless-DOM test that loads the real `index.html`/`app.js`
and: confirms System's position and default-safe ordering, confirms an
empty section shows an inline prompt rather than redirecting on mere
hover, confirms an explicit confirm on that prompt does redirect, and
confirms a simulated OS key-repeat event does not double-fire an action.

## Major feature additions (this revision)

**Carousel navigation, pivoting at Apps.** Categories at or before Apps
render in a fixed left-to-right row, same as before. Moving past Apps
turns the row into a circular carousel: whichever category is highlighted
always slides into Apps' slot (animated via FLIP position transitions on
persistent DOM nodes, not re-created each time), and anything that scrolls
off the left loops back around to reappear queued behind System. Works
symmetrically in both directions. Independently, the highlighted category's
icon is kept horizontally aligned with the icon column of whatever list is
showing below it — measured live via `getBoundingClientRect` each render
rather than hand-tuned, so it stays correct regardless of section content.

**On-screen keyboard.** Automatically appears below any focused text/
password field (the "add custom section" name field, the Wi-Fi password
field), fully navigable by game controller (D-pad/stick moves the
highlighted key, confirm types it, back closes it). Real physical keyboard
typing keeps working the entire time — the on-screen keyboard is an
additional input method, not a replacement.

**Files, restructured.** Now a two-item list instead of a single direct
action: **Meridian Explorer** (launches `Meridian_Explorer.exe` from the
app's own folder, if present) sits above **Windows File Explorer** (the
previous "open This PC" behavior).

**System, expanded.** Added, in order, after Control Panel: **Recycle
Bin**, **Uninstall Apps** (opens `ms-settings:appsfeatures`), **Wi-Fi**, and
**Bluetooth** — the last two open a dedicated network overlay (scan,
connect, disconnect). Wi-Fi is fully functional via `netsh` (open and
WPA2-Personal networks; enterprise/802.1X isn't supported by this simple
path). Bluetooth is honest about a real Windows limitation: pairing a
*new* device fundamentally requires the OS-level pairing ceremony (PIN
confirmation, etc.), which can't be scripted headlessly, and most audio
devices use classic Bluetooth rather than BLE, so there's no equivalent of
`netsh` to reach for. What's implemented instead: listing devices Windows
already knows about, and connect/disconnect for already-paired ones (via
enabling/disabling the PnP device, which typically needs Meridian running
as Administrator), plus a direct link to Windows' own Bluetooth settings
for pairing anything new.

**Video player.** Game-controller playback controls while a video is open
— confirm toggles play/pause, left/right seeks ±10s, up/down adjusts
volume, back closes (keyboard equivalents work too). A **Video Fullscreen**
toggle in Settings switches between the default letterboxed view and an
edge-to-edge fullscreen view. The webview now explicitly requests the
`edgechromium` (WebView2) backend for hardware-accelerated video/UI
rendering.

**Index/thumbnail cache.** Music/Photos/Videos scans now cache metadata
and thumbnail paths keyed by file mtime — unchanged files are served
straight from cache on every subsequent scan instead of re-reading tags or
regenerating thumbnails, which matters a lot once a library has thousands
of files. Verified directly: touching a file forces exactly one rebuild;
untouched files trigger zero.

**Load Subfolders toggle** (Settings, between Video folders and Apps).
When off, Music/Photos/Videos switch from automatic recursive scanning to
manual folder browsing: a sidebar appears on the left listing your
configured folders and the current directory's subfolders, click to drill
in, and Back (Space / controller B) goes up one level.

**Bigger preview pane.** Music/Photos/Videos now show an enlarged preview
of the currently-selected item in a panel on the right.

**Battery indicator.** Shows under the clock as an icon + percentage when
the device has a battery and the **Battery Level Indicator** setting is
on; hidden automatically on desktops with no battery.

**Macro rename.** "All Other Programs" is now labeled **"Close all other
programs"** (same behavior).

Verified with an expanded headless-DOM suite covering: carousel ordering
and direction at every stage (static → sliding → wrapped → back to
static), the Files restructure and its launch wiring, the macro rename,
System's exact new ordering, the Wi-Fi overlay's scan/list flow, the
on-screen keyboard's controller-typing path and its coexistence with real
keyboard input, and the video controller controls (play/pause toggle,
seek, volume, close) — plus a Python-side suite confirming the index
cache actually skips rebuilding unchanged files and rebuilds changed ones,
subfolder browsing returns correct non-recursive listings, and all the new
Windows-only actions (Recycle Bin, Uninstall Apps, Wi-Fi, Bluetooth) fail
gracefully rather than crash when run outside Windows.


## Scope notes

- This is an original UI - no proprietary code, artwork, or branding is used
  anywhere in it.
