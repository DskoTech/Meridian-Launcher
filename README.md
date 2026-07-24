# Meridian Launcher

A cross-bar style desktop front-end / app launcher for Windows: one
horizontal row of sections, a vertical list per section, navigable by
keyboard, mouse, or game controller.

**This build targets Windows only.** Most of its features — launching
.exe/.bat files, opening Explorer/Control Panel/Task Manager, shutdown/sleep/
hibernate, and controller support — are Windows-specific, so there's no
meaningful cross-platform version of this particular feature set.

See also: **CHANGELOG.md** (dated, itemized history of every revision),
**FEATURES.md** (what the whole suite does, section by section), and
**CUSTOMIZATION.md** (themes, Plugins, settings, everything you can
change without touching code).

## License

**DskoTech Source Available License 1.0** — see `LICENSE.txt` for the
full text. In short: free to view, study, compile, modify, and run for
personal/educational/research/non-commercial use, and to fork for your
own experimentation or to submit pull requests back — but not to sell,
offer as a paid service, redistribute a modified version, or use
Meridian Launcher's branding/trademarks/artwork, without DskoTech's
written permission. This is source-available, not open source in the
OSI sense — `LICENSE.txt` is the authoritative text if anything here
reads ambiguously.

**`obsolete/`** holds files identified as superseded by later work but
not deleted — see `obsolete/README.md` for what's there and why, if you
want to review and decide whether to actually remove them.

## Latest revision — four new controller-first plug-ons, real Bluetooth
## pairing, streaming/login fixes, and a round of crash fixes

**New plug-ons** (System/Apps/Streaming sections, all off by default —
enable from Settings > Plugins): **Task Manager** (CPU/RAM per running
app, controller-navigable Focus/Close grid), **Display & Audio**
(resolution/refresh rate/HDR toggle/audio output device, one panel),
**Wi-Fi & Bluetooth** (real scan-and-pair for new Bluetooth devices —
not just toggling already-known ones — plus an on-screen keyboard for
Wi-Fi passwords), **Type from Phone** (QR code + a phone's own keyboard,
for typing long passwords/search terms without clicking them out one
character at a time on the on-screen keyboard), and **HyperBeam** (a
Streaming entry for hyperbeam.com's shared-browser watch-together tool).
Each runs its own tiny local web server and talks to the rest of the
suite through it — see each `*_server.py`'s module docstring.

**Universal on-screen keyboard auto-invoke** (`onscreenmenu`): the fake
cursor already worked against any window with no button press needed;
the keyboard didn't. Now `osk.exe` opens automatically the instant a
non-Meridian window (a third-party installer, anything Meridian doesn't
know about) takes focus — no more remembering to press X first. Also
makes a best effort for UAC/Secure Desktop prompts specifically, though
that one has a real OS-level ceiling on what's possible from outside a
signed accessibility app — see `foreign_focus_watcher.py`'s docstring
for exactly what is and isn't achievable there.

**CyberDeckBrowser**: real persistent logins (was never given a stable
storage path or cookie policy — sites' own "forget me on close" session
cookies were winning every time), proprietary-codec/DRM streaming fixes
(`--ppapi-widevine-path`, `--autoplay-policy`, a real desktop Chrome
User-Agent, `PluginsEnabled`), and each simultaneously-open boxed window
(Browser section, each webapp plugin) now gets its own isolated profile
storage instead of one shared path — sharing one caused a real bug where
a second simultaneously-open window's Chromium renderer would silently
fail to come up at all (Qt chrome still rendered fine, browser content
area stayed blank) due to Chromium's own same-profile-two-processes
lock. Web section's own "CyberDeckBrowser" entry now always opens the
program directly instead of occasionally getting routed through the
URL-opening/Browser-section logic meant for actual links.

**Settings > Backup & Restore**: export/import settings, selected theme,
activated plugins, and custom sections/plugins as one `.zip`.

**Settings > About**: a full third-party attributions/licenses list —
every bundled dependency and redistributed Microsoft runtime component,
with its license type.

**gameinput_native** (the real Microsoft GameInput SDK backend, see
`gameinput_native/README.md`) got a real diagnosis-and-fix pass:
`Settings > Controls` now always reports exactly why the native backend
isn't active when it isn't (not built / built but shadowed / wrong
Python ABI / runtime DLL missing), a `build_and_deploy.py` script builds
it and stages it to every app folder in one step, and — the actual root
cause of it silently never working even when "successfully" built — the
PyInstaller `.spec` files now exclude the `gameinput_native/` source
folder from analysis (it was getting baked into frozen builds as a
hollow placeholder that permanently shadowed the real, externally-placed
`.pyd`), paired with an explicit `sys.path` fix so the real file can
actually be found once that hollow placeholder is gone.
`InstallMeridianSuite_WithGameInputBuild.bat` is a new variant of the
main installer that also installs the MSVC Build Tools needed to build
it (real `vswhere`-based detection, skips entirely if already present)
— kept as a separate file since that's a much bigger download most
people don't need.

**Crash fixes found via real compiled-build reports**: `audio_devices.py`
no longer crashes the whole app at startup when `pycaw`/`comtypes`
aren't bundled (degrades to "unavailable" in the UI instead, the way an
optional feature should); the `QWebEngineProfile` import in
CyberDeckBrowser's own persistent-login fix above was pointed at the
wrong PySide6 module and crashed the browser on every single launch
until caught against a real crash log.

## Plugins, Explorer/Browser sections, and a batch of
## real bugfixes

This pass added a full plugin system and two new embedded-app sections,
then went through several rounds of bug reports against them (plus some
long-standing bugs found along the way that predate this work entirely).

**New:**
- **Plugins system**: a `Plugins/` folder next to the exe, auto-scanned on
  startup and from Settings > Plugins. Two plugin types: `"list"` (a plain
  data-driven list, like the bundled **Start** plugin — pulls your Windows
  Start Menu into a section) and `"webapp"` (boxes a **Meridian NetBrowse**
  instance pinned to one site into its own section — used for the
  **Telegram / Discord / Messenger / Snapchat / Phone Link** plugins,
  Phone Link pointed at Google Messages for web). An `examples/` folder
  holds a heavily-commented blank-plugin template. Plugins are hidden by
  default; enable them from Settings > Plugins, no restart needed.
- **Explorer section**: right after Desktop when enabled. Desktop folders
  now show up in the Desktop section and open into this section (boxing
  **Meridian FileBrowse**, a separate-source-files fork of Meridian
  Explorer) if it's on, or standalone Meridian Explorer / Windows Explorer
  if it's off.
- **Browser section**: right after Explorer when enabled. Internally-
  launched URLs open here (boxing **Meridian NetBrowse**, a fork of
  CyberDeckBrowser) if it's on, or CyberDeckBrowser / the system default
  browser if it's off.
- **Meridian FileBrowse** and **Meridian NetBrowse**: both boxed into
  their section's list-frame area rather than full-screen, both fully
  exit ("Exit Program") back to the Sections bar, and Meridian Launcher's
  own controls come back automatically when they close. Both build as
  single `.exe` files with no visible console.
- **System section**: added Command Prompt, PowerShell, Microsoft Store,
  and Windows Update.
- **Game Library**: non-big-5 platforms (anything besides Steam/GOG/Epic/
  Amazon/Luna) now get their own section per platform instead of one
  shared "Other" bucket.
- **Photos**: Start button over a photo opens an Edit / Set as Background
  popup. Edit uses the file's actual associated "edit" program rather than
  hard-requiring `mspaint.exe`.
- **Controller input backend**: XInput is now the default (Settings >
  Controls has a cycle button for XInput / GameInput / DirectInput / SDL3
  / Auto). GameInput's vtable-probing approach turned out to only
  reliably decode buttons, not sticks/triggers, across multiple
  independent test reports — a real bug in that approach, not one
  person's hardware — so it's opt-in now instead of the default.

**Fixed** (see CHANGELOG.md for the full list): item-panel showing at
launch before a section was picked; several z-index/paint-order bugs in
the Factory Central theme; the compiled build not finding `Plugins/`
(PyInstaller's temp extraction folder was being used instead of the real
exe folder); `osm.bat` toggling onscreenmenu closed instead of just
not re-opening it; onscreenmenu's single-instance check false-positiving
against its own PyInstaller bootloader process on every compiled launch;
a dead-code bug in Meridian Explorer/FileBrowse where the controller's
D-pad/stick/A/B never actually reached the options popup (keyboard
worked because it's a separate, correctly-structured code path); boxed
apps sometimes measuring the panel's on-screen position before its
slide-in animation had actually moved it there.

## Earlier revisions

Renamed the program (internally and externally) from **Meridian** to
**Meridian Launcher** — window title, app title, build output
(`Meridian Launcher.exe`), and docs.

- **Kiosk mode is now a real lock**, not just a window style. Turning it on
  from Settings shows a controller-selectable confirmation prompt that
  discloses all three ways back out, and once it's on, **Settings and
  System both disappear from the category row entirely** (so there's no
  "toggle it back off" button sitting right there). The only ways out:
  hand-editing `window_mode` in `settings.json`, holding the controller's
  **Y** button for **45 seconds**, or entering the unlock code — **D-pad
  Up, Up, Down, Down, Left, Right, Left, Right, B, A** on a controller, or
  **Up, Up, Down, Down, Left, Right, Left, Right, B, A** (literal keys) on
  a keyboard. Both codes work off the raw physical button/key, independent
  of whatever confirm/back are remapped to. A toast confirms
  `kiosk mode disabled` once any of these succeed.
- **Removed the auto-launch of `onscreenmenu.exe` at startup.** In its
  place: a **"Launch with onscreenmenu?"** toggle (on by default) on each
  of Apps/Games/Emulators/Chat/Streaming/custom sections — when on,
  launching anything from that section's list also runs `osm.bat` from the
  app's folder. A second global toggle, **"Launch External System features
  with onscreenmenu?"** (also on by default), does the same for Task
  Manager, Control Panel, Recycle Bin, Uninstall Apps, and "Open Windows
  Bluetooth settings" from the System section.
- **Web's CyberDeck Browser option now launches `CyberDeckBrowser.exe`**
  (was `CyberDeck.exe`).
- **Games gets a permanent "Game Library" entry** pinned at the top of the
  list, launching `Meridian Game Library.exe` from the app's folder.
- **Battery indicator shows a full battery on desktops.** If the OS reports
  no battery hardware at all (the normal case on a desktop), the indicator
  — when enabled — now shows a full charge instead of hiding itself.
- **Revert to factory settings**, the very last option in Settings, clears
  every saved user modification back to defaults behind a controller
  selectable Yes/No confirmation.
- New `install_dependencies.bat` and `compile.bat` for a from-scratch
  Windows build without typing any commands by hand.

## This revision — built on your uploaded files

Started from the zip you uploaded (which turned out to be my build from two
turns back, plus your style.css edits) and kept every one of your changes
exactly: the horizon glow line at `top: 76px`, the category row `gap: 86px`,
and the preview pane's `transform: translateX(-100px)`. Your real
`settings.json`, `.cache`, `keyboard_controls.json`, and
`controller_controls.json` were left untouched too — only the source files
changed.

**Category row no longer bleeds into the clock area.** The row was
previously clipped by `overflow: hidden` on itself, but since it's also the
element that gets transformed (for carousel sliding and list-icon
alignment), the clipping boundary moved along with it — so far-right
slides could visually push icons/labels past where they should've been cut
off, into the clock's space. Fixed by wrapping it in a stable
`#category-viewport` that never moves; the inner `#category-row` still
transforms freely, but now clips against a fixed boundary, so anything
sliding toward the clock disappears right at the boundary and reappears
correctly once it slides back.

**Settings is now controller/keyboard navigable**, same as every other
section: Up/Down moves a highlighted-outline cursor over its buttons/
toggles/radio-pills in visual order, confirm clicks whichever one is
highlighted. Left/Right still change category as usual. Text inputs (add
custom section, Wi-Fi password) aren't part of this cursor — they get real
focus directly when their modal opens, same as before.

**Item list is now pinned at a fixed horizontal position** — `margin-left:
25vw`, which computes to exactly 480px at 1920px-wide (1080p) and scales
proportionally at other resolutions, rather than staying centered based on
whatever else happens to be on screen. The subfolder sidebar and preview
pane became absolutely positioned (left/right edges) so they no longer
compete with the list for flex space.

**Web, restructured** the same way Files was: now a two-item list —
**CyberDeck Browser** (launches `CyberDeckBrowser.exe` from the app's own
folder, same pattern as Meridian Explorer) sits above **Default Browser**
(the previous single-action behavior).

Wi-Fi/Bluetooth name listings in System, and the folder-focus Left/Right
navigation for Music/Photos/Videos, were both already present in your
uploaded checkpoint (from two turns back) and are confirmed still working
here — re-verified rather than rebuilt.

Verified with a headless-DOM regression pass across all prior test suites
(carousel ordering/direction, Files restructure, System ordering, on-screen
keyboard, video controls, folder-focus navigation, battery indicator) plus
new tests confirming: Web's restructure and both its launch paths, and
Settings' cursor starting at index 0, moving correctly with Up/Down, and
confirm correctly activating whatever control it's currently on. The fixed
480px/25vw positioning and the clock-area clipping are structurally
correct and consistent, but pixel-exact visual verification needs a real
browser — this sandbox can't render real CSS layout.

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

## Startup behavior

- If a file named `Meridian_Explorer.exe` exists in the same folder,
  selecting "Meridian Explorer" from the Files section launches it
  on-demand (not at startup). If it's missing, that option reports a clear
  error instead of failing silently.
- The same applies to `CyberDeckBrowser.exe` (Web section's "CyberDeck
  Browser") and `Meridian Game Library.exe` (Games section's "Game
  Library" entry, pinned at the top of the list).
- `osm.bat`, if present in the app's folder, is launched alongside items
  from exe-list sections and alongside certain System features — see
  "Launch with onscreenmenu?" in Settings — rather than being auto-launched
  at startup the way `onscreenmenu.exe` previously was.
- If an opening video is configured, it plays before anything else.

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

## XMB-style redesign (this revision)

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

## Bugfix pass (earlier revision)

Found and fixed by re-tracing every code path and actually exercising the
Python logic with the Windows-only pieces mocked out:

- **Macros could never launch `.bat` files.** Windows can't `CreateProcess`
  a `.bat` directly the way we were calling it — it needs to go through
  `cmd.exe`, same as double-clicking would. Now uses `os.startfile`, which
  resolves file associations correctly for both `.exe` and `.bat`.
- **The overlay feature would silently never appear.** It reads pixel data
  from the overlay image via canvas, which requires a CORS header from our
  local media server; that header was missing, so the image load was
  rejected outright. Added `Access-Control-Allow-Origin: *`.
- **`macros_whitelist` was structurally nested inside `sections`**, a dict
  that's otherwise assumed to only contain `{"items": [...]}` objects —
  latent crash risk. Moved to its own top-level settings key, with a
  migration path that preserves any custom whitelist entries from a
  previous install instead of discarding them.
- **Settings could randomly kick you back to the category row** on a Down
  press, depending on leftover cursor state from whatever section you were
  in before. Settings now always ignores directional nav instead of
  sometimes falling through to it.
- **Icon extraction had a GDI double-release bug** (`DeleteDC` called on a
  DC that should only ever be `ReleaseDC`'d), which risked corrupting
  Windows' GDI handle table over a long kiosk session with lots of icon
  extraction. Fixed to release each DC the correct way exactly once.
- **System actions (shutdown/sleep/hibernate/Control Panel/Task
  Manager/Web/Files) had no error handling** — if one ever failed (blocked
  by policy, not on PATH), the exception vanished into an unhandled promise
  rejection with zero user feedback. They now report success/failure and
  the UI shows a toast on failure.
- Hardened the XInput binding with explicit `argtypes`/`restype` instead of
  relying on ctypes to guess the calling convention.
- Recognized keys (confirm/back/up/down/left/right) now call
  `preventDefault()`, so the browser's own space-bar-scrolls-the-page and
  arrow-key-scrolls-a-div behaviors can't visually fight the app's own
  navigation.

Verified with a mocked-`webview`/mocked-`win32` test harness exercising
settings persistence, folder management, exe-section CRUD, custom sections,
macros, and the process-whitelist logic (confirmed core OS processes and
the app's own process always survive "All Other Programs," and everything
else gets closed). Still worth a real smoke test on Windows hardware,
particularly controller polling and window-mode switching, since this
sandbox can't run pywebview/XInput/win32 for real.

## Scope notes

- This is an original UI - no Sony code, artwork, or branding is used
  anywhere in it.
