# Meridian Suite — Changelog

Gamepad-first, XMB/cyberpunk-styled Windows desktop suite by
Samuel "Zenith" Schimmel (Madisico), under the DskoTech brand.

The suite is five apps built together:

| App | Stack |
|---|---|
| **Meridian Launcher** | Python + pywebview (HTML/CSS/JS frontend) |
| **Meridian Game Library** | Python + pywebview, Playnite-backed |
| **CyberDeckBrowser** | PySide6 / QtWebEngine |
| **Meridian Explorer** | pygame |
| **onscreenmenu** | pygame/Qt transparent controller overlay |

Plus `Meridian_Exporter` (a PowerShell extension for Playnite) and the
`InstallMeridianSuite` toolchain.

> **A note on completeness.** Detailed per-version records exist from **v15**
> onward. Versions **v1–v14** predate the current development record; they're
> summarized below by feature area rather than by version number, because
> assigning specific features to specific early version numbers would be
> guesswork.

---

## v1–v14 — Origins (summarized; no per-version record)

The era that took Meridian from a single HTML file to a working suite.

- **Meridian Launcher** began as a Sony VAIO Media Plus / XMB clone
  ("Horizon Bar") in a single HTML file, then grew into a full
  Python/pywebview Windows launcher: XInput controller support, media
  indexing (music/photos/videos), subfolder browsing, Wi-Fi and Bluetooth
  management, and icon extraction via `ExtractIconEx`.
- **Meridian Game Library** pivoted away from per-storefront OAuth to a
  Playnite-backed architecture: the `MeridianExporter` PowerShell plugin,
  a `MeridianFS` Playnite theme, a 5-column tile gallery with wobble
  animation, a filter sidebar, silent background Playnite sync, and direct
  game launching via resolved Play actions.
- **CyberDeckBrowser** grew a cyberpunk HUD overlay, CRT/scanline/glitch
  effects, a startup loading screen, a first-boot prompt, focus-aware
  cursor/HUD disabling, and `osk.bat` integration. Fixed a shiboken6 DLL
  crash under PyInstaller via `--collect-all`.
- **onscreenmenu** was built from a stripped CyberBrowser codebase into a
  transparent fullscreen controller overlay: fake cursor, Y-button shortcut
  menu, X-button key-combo menu, recent-apps switcher, Start+Select
  hibernate, L3+R3 quit, and self-install to Program Files. Fixed Qt's
  `quitOnLastWindowClosed` firing on early dialogs.
- **Meridian Explorer** established the dual-pane, controller-driven file
  browser.
- Kiosk mode, per-section onscreenmenu toggles, factory reset, and a
  battery-indicator fix landed in the Launcher.
- App data moved to `%LOCALAPPDATA%\Meridian Launcher\` with per-app
  subdirectories and legacy migration. Added `CompileAndPackage.bat` and a
  GitHub Releases update checker.

---

## v15 — GameInput migration

- Audited and completed a mid-flight migration to a shared `gameinput_api.py`
  with an XInput fallback.
- Wrote `onscreenmenu`'s missing `controller_thread.py` from scratch.
- Wired Meridian Explorer's `SDLJoystickShim` to GameInput.
- Diagnosed the Xbox Full Screen Experience problem: Windows stops delivering
  XInput data to background processes (input focus arbitration, not process
  suspension). Identified Microsoft's GameInput API as the correct path.

## v16 — Theme color + Playnite filter sections

- Per-theme "primary theme color" for DawningHorizon in both the Launcher and
  the Game Library: light/dark/neon/primary/pastel/bubblegum palettes across
  ROYGBIV hues, with ROYGBIV-complementary section colors.
- Playnite custom-filter-section toggle (`playnite_filter_sections`).

## v17 — Controls reference + Start menu

- Controller-controls reference block at the top of Settings in all three
  web-based apps.
- `CONTROLS_README.txt` at the repo root covering all five apps.
- Credit footer on every settings screen.
- Game Library Start-menu (Start / Tab): hide game (with confirm), unhide,
  rename title, show/hide hidden games, close program. Backed by
  `hidden_games`, `game_renames`, and `show_hidden_games` settings.

## v18–v23 — Installer toolchain

- **v18** `InstallMeridianSuite.bat`: self-elevating, installs Python 3.12.8
  and pip dependencies, compiles all apps, stages to
  `C:\Program Files\DskoTech`, installs WebView2 + VC++ redistributables.
- **v19** `.exe` wrappers cross-compiled with MinGW — the batch is embedded
  as a byte array, extracted to `%TEMP%`, with the real repo directory passed
  via a `MERIDIAN_ROOT` environment variable.
- **v20** ffmpeg/ffprobe extracted into the DskoTech folder and added to the
  system PATH.
- **v21** `MeridianSuite-Dependencies.zip` offline bundle; installers prefer a
  local `Dependencies\` folder over downloading.
- **v22** `DownloadDependencyInstallers.bat`/`.exe` (no admin — fetches the
  offline bundle).
- **v23** `InstallDependenciesOnly.bat`/`.exe` (runtime dependencies only, no
  Python install or compile).

## v24 — Open-programs bar (taskbar replacement)

- `tasks_win.py` enumerates taskbar-visible windows via ctypes
  (WM_GETICON → class icon → exe icon fallback, rendered to a PNG data URL),
  with `focus_task` / `close_task`.
- Frontend: X jumps to the bar, A refocuses, B returns to sections, hold-X 3s
  closes (with confirm unless "Close tasks without prompt" is set).
- `TASKBAR_PLACEMENT` map for per-theme positioning.

## v25 — Controller status indicator

- Live controller-API indicator in all three settings screens
  (GameInput/XInput/SDL/none + connected state, color-coded, 2s refresh).

## v26 — Meridian Explorer shell integration

- Explorer accepts a folder argument: handles quoted paths, paths with spaces,
  `file://` URLs, and resolves a file path to its containing folder.
- `MeridianExplorerShellIntegration.bat` — three modes (context menu,
  default folder handler, remove), all under `HKCU` so no admin is needed and
  everything is reversible.
- Launcher "Open folders in Meridian Explorer" toggle; folders became
  first-class launchable section items.

## v27 — Built-in editors + icon size

- `meridian_editors.py`: text and hex editors with a strict two-box layout —
  the document viewport scrolls internally (so the keyboard can never cover
  the line being edited) above a prominent virtual keyboard with a wide
  **VOICE INPUT** button (synthesizes Windows' Win+H voice typing).
- Explorer menu grew Edit, Hex Edit, and Open With… (Notepad / WordPad /
  Paint / Default / the Windows "choose app" dialog).
- Launcher icon-size setting: small (36px) / medium (72px) / large (144px) /
  XL (288px), CSS-variable driven, with rows growing to fit.

## v28–v32 — Theme system overhaul

- **Audio fix:** prev/next/random now use a persistent music queue captured
  when playback starts, instead of walking the *current* section (which is
  why photos loaded when skipping tracks from the Pictures section).
- Fullscreen returned to `exclusive_fullscreen` as the global default.
- `theme_assets.py` renders per-theme, per-app placeholder background and
  overlay PNGs (12 files per app) with Pillow; self-healing on first run.
- Per-theme custom background **and** overlay: settings moved from single
  values to `{layout: path}` dicts with automatic migration. Animated `.gif`
  backgrounds supported.
- Controls hint text removed (markup kept, commented, for future use).
- DawningHorizon: sections bar scrolls left/right; mspaint-style color grid
  (24×8 HSV + grey ramp) added beneath the named palettes, storing
  `hex:#rrggbb`.
- CyberRadial: the square focus projection became a round radial glow centered
  on the hub, wrapping the section buttons and the 3D orb together.
- Verticular Blobs overhauled in both apps: fixed options box with internal
  scroll, clock relocated, wireframe/orb removed, backgrounds matched.
- Taskbar placements activated across all themes; the whole taskbar system was
  **ported to the Game Library**, which had none.

## v33 — Focus gating + Playnite behavior

- Playnite no longer auto-launches when the gallery opens; syncing is now an
  explicit action.
- Focus gating: both apps poll `is_foreground()` every 400ms. Controller input
  is still *received* in the background (so the foreground combo works) but
  doesn't navigate until the window is focused.
- Configurable foreground trigger: Start+Select, the Xbox/Guide button, or off.
- Installer now stages and runs `ImportMeridianexporter.bat`.

## v34–v36 — Render regressions + vertical taskbar

- **Fixed a fatal boot crash** that left only the background and clock on
  screen. Two causes: `[...bar.classList]` (spreading a live `DOMTokenList`)
  threw in `applyTaskbarPlacement`, and — the actual culprit — removing the
  hint text left `boot()` calling `.textContent` on now-commented-out spans,
  throwing a `TypeError` before `applyAccent()` / `renderCategories()` ever ran.
- `applyTaskbarPlacement` is now wrapped in try/catch so the open-programs bar
  can never take the whole layout down with it.
- Vertical taskbar items stack in a column; the DawningHorizon name bubble
  displays to the *left* of the bar (it sits at the screen's right edge).

## v37 — Guide button + Playnite filter presets

- **Guide button:** the GameInput→XInput mapping table was missing the Guide
  button entirely, so presses were silently discarded. Added
  `0x00004000 → 0x0400`.
- GameInput failures became self-diagnosing: `open_gamepad` records
  `LAST_BACKEND_ERRORS`, surfaced in the settings status line.
- **Playnite filter presets:** the exporter called
  `GetGameMatchesFilter` — *which doesn't exist in the Playnite SDK* — so every
  preset silently came back empty. Rewrote it around the real
  `GetFilteredGames`, with a working local fallback covering name/installed/
  favorite/hidden/Source/Genre/Platform/Category. Errors now surface via a
  dialog, and the manual export reports its preset count. Exporter → v1.1.

## v38 — Cleanup, commenting, user themes

- Removed 7 genuinely orphaned JS functions (verified against the frontend and
  boot-simulated). The Python side audited clean — the apparent orphans are
  pywebview `Api` methods called from JS.
- Both stylesheets gained a "STYLESHEET ARCHITECTURE" header documenting the
  theme-class system and every CSS custom property, plus labeled section
  dividers per theme.
- **User custom themes**: drop a `.css` file (or a folder with `theme.css` and
  an optional `theme.json`) into `themes/`. Each is discovered by
  `user_themes.py`, listed in the Layouts picker, and applied as
  `body.layout-user-<slug>` layered on a chosen built-in base — so a theme
  only overrides what it wants. Ships with two example themes.

## v39 — Quick fixes

- "Open folders in Meridian Explorer" won't enable when the Explorer exe is
  absent; shows a disabled explanatory row instead.
- Single-pane mode hides "Move/Copy 2 Other Side".
- Taskbar mouse behavior: double-click opens, press-and-hold 3s closes on
  release. The task-name bubble unloads when the bar isn't focused.
- Settings keeps its scroll position across re-renders, and navigates 1.3×
  faster via a context-aware cooldown scale.
- onscreenmenu now auto-launches for the Windows "Choose App" dialog and when
  opening non-Meridian programs, so those windows are controller-drivable.

## v40 — Settings restructure + 2D color grid

- Settings split into five groups (Controls / Sections / Themes / Program /
  About) via an `appendChild` proxy that tags each block with its group — no
  risky reordering of the ~550 lines that build them.
- **Color selector 2D navigation**: the mspaint grid is now a *single* entry in
  the settings cursor instead of 192, with a 2D sub-cursor and edge-release —
  it was previously impossible to navigate past.

## v41 — DawningHorizon layout

- Sections bar navigates by left/right (up/down had been scrolling sections in
  every theme).
- Clock/battery moved to the bottom-right; the open-programs bar fills the
  column above it, widths matched.

## v42 — Meridian Explorer overhaul

- **View submenu**: Text / List / Icon / Gallery modes, mirroring the
  Launcher's list and gallery navigation (left/right within a grid row,
  up/down by a full row), all with fixed panes and internal scrolling.
- **Sort submenu**: Name / Size / Type / Date, ascending or descending.
- **Day/night mode**: the entire palette is swappable; "System" follows
  Windows' `AppsUseLightTheme`.
- **Undo/Redo Move**, **Select All** (B selects none), **Search**,
  **Properties** (Windows-like popup), and **Set as Background** for images
  (Stretch/Center).
- **Quick Access mode**: "Switch Pane Modes" now cycles Dual → Single → Quick
  Access, where the main pane takes ~5/6 of the width and a Windows-style rail
  lists This PC, Downloads, Pictures, Videos, Documents, Music, custom
  shortcuts, and every mounted drive.
- Fixed `display_name_of` crashing on drive entries lacking a volume label.

## v43 — Regression fixes

- **Game Library restored**: a missing `applyUserThemeClass()` (the call was
  ported but the function wasn't) threw a `ReferenceError` at boot and no
  sections loaded.
- **Sections bar A/Enter restored**: the `settings` branch in
  `activateCurrentSelection` ran *before* the sections-focus check, so A never
  confirmed a section while on the Settings category.
- **GameInput `QueryInterface`** was called without its `this` pointer
  ("takes 3 arguments, 2 given"); `GetCurrentReading` had the same bug. Audited
  every COM call's arity.
- Settings restored to a **single section** whose landing screen is a list of
  the five options (not five separate sections).
- DawningHorizon clock pinned bottom-**right** (a base `left: 24px` rule was
  winning); taskbar width halved to match the clock block.
- **Custom background file picker fixed**: `IMAGE_FILE_TYPES + [("GIF", …)]`
  concatenated a tuple of filter strings with a list of tuples, raising
  `TypeError` so the dialog never opened.
- **Overlay now draws on top** (`z-index: 1` → `40`; it was rendering beneath
  the entire UI).

## v44 — Boot + input fixes

- **Launcher windows restored**: `SETTINGS_OPTIONS` was a `const` declared
  *after* its first use on the boot path — a temporal-dead-zone
  `ReferenceError` that killed rendering. Hoisted, and both apps audited for
  the same pattern.
- **Game Library controller thread crash**: `_x_hold_start` was used in the
  poll loop but never initialized. Added an AST audit that checks every
  `self.` attribute read against what `__init__` assigns.
- pywebview's deprecated `OPEN_DIALOG` / `FOLDER_DIALOG` replaced with
  `FileDialog.OPEN` / `.FOLDER`, with a fallback for pywebview < 5.x.
- Added a functional flow test harness covering the settings menu, sections
  confirm, and taskbar loading — rather than syntax checks alone.

## v45 — GameInput actually reads the pad

- **The real GameInput bug.** After v43 fixed initialization, GameInput loaded
  cleanly but the controller still did nothing. The cause: on Windows 11 the
  V1 interface matched, which selected **vtable slot 17** for
  `IGameInputReading::GetGamepadState` — but slot 17 is `GetTouchCount`. The
  documented slot is **22**. GameInput was faithfully calling the wrong
  function forever, which is why it looked healthy and reported no input.
  `IGameInputReading` has the same layout regardless of which `IGameInput`
  version is queried, so 22 is correct for both.
- Added an empirical safety net: `GAMEPAD_STATE_SLOTS = (22, 23, 17)` is probed
  on the first reading and the winner cached, guarded by
  `_plausible_gamepad_state()` — stick/trigger ranges, NaN, and unknown button
  bits are rejected, so calling a wrong slot degrades to "try the next one"
  instead of silently feeding garbage (or dead input) to the app.
- The settings status line now reports the detected reading slot, so a future
  layout surprise is visible rather than invisible.

## v46 — Input debugger, XInput toggle, Factory Central

- **Prefer XInput toggle** (Settings → Controls): forces the proven XInput
  backend and restarts the listener live, no relaunch. GameInput remains the
  default (it's the only path that reports the Guide button).
- **Controller debugger** (Settings → Controls): a live readout of the whole
  input pipeline — backend chosen, controller connected, app focused,
  GameInput poll/reading/state counters, the last `GetCurrentReading`
  HRESULT, per-slot probe results with the reason each was rejected, the raw
  pad state (buttons/triggers/sticks), and the last action to reach the UI.
  Whichever line stops updating is the broken stage.
- **Loosened the state plausibility guard**: it had been rejecting any state
  carrying a button bit outside the known map, which would turn one unmapped
  button into total input loss. Only the float ranges (and NaN) are checked
  now — a wrong vtable slot still gets caught by those.
- **`--orbit-full`**: themes can opt into a full 360° section ring instead of
  CyberRadial's ±90° arc, read from computed style so a pure-CSS user theme
  can drive it.
- **Factory Central** user theme: the section selector as one big industrial
  gear — a notched teeth ring (masked `repeating-conic-gradient`), a machined
  rim, and a thick hollow cylinder hub with a real bore, with sections riding
  a full 360° orbit between hub and teeth. Built on CyberRadial, so all of
  its behavior is inherited. Oiled-steel and hazard-amber palette.

## v47 — GameInput slot from field data, overlay toggle, Explorer menus

- **GameInput reading slot, corrected by field data.** The debugger reported
  slot 22 raising an *access violation* on the in-box Windows 11
  `gameinput.dll`, with slot 23 accepted. So that DLL's `IGameInputReading`
  carries an extra vtable entry ahead of the state getters, and the docs don't
  describe it. Slot order is now `(23, 22, 24)` — the shipping layout first,
  which also means the crashing slot is never touched on those machines.
- **Decisive slot verification**: the debugger now accumulates every button
  bit and any stick/trigger movement ever seen. A wrong-but-plausible slot
  returns zeros forever, which is indistinguishable from an idle pad in a
  single sample — press everything, and if "input ever seen" stays NO, the
  slot is wrong.
- **Themes auto-scan at startup** — `loadUserThemes()` was only wired to the
  picker and the rescan button, so a dropped-in theme needed a manual rescan.
- **Overlay show/hide** on the **Left Trigger** (the only controller input the
  suite doesn't already use — every face button, shoulder, stick-click,
  Start/Back and Guide are spoken for) and the **O** key.
- **Meridian Explorer**: Y now hands control to the options menu immediately
  (the same frame no longer continues driving the file panes); the Quick
  Access rail gets **its own menu** (Open/Copy/Cut/Paste, plus *Remove from
  List* for user-added shortcuts only, never for built-ins); and the "other
  side" actions are hidden in Quick Access mode as well as single-pane.
- **Game Library**: full window-mode parity with the Launcher
  (Exclusive Fullscreen / Windowed Fullscreen / Windowed — Kiosk deliberately
  omitted, since the Game Library has none of the Launcher's unlock paths and
  would strand the user); theme color moved to the bottom of Settings.
- **Playnite filter-preset diagnostics** in Game Library settings: the exact
  file the reader opens, whether it exists, its size/shape/preview, raw vs
  parsed counts, and the preset names — so this stops being guesswork.
- **Factory Central**: gear centered; section names rotate with the gear;
  options list moved top-right with a sawtooth cut, sliding in from the right
  to fully cover the gear and fading out over 2s when B returns focus to the
  sections; thumbnail and subfolder bar swapped to the top-left; taskbar
  horizontal along the bottom-left, stopping before the clock/battery.

## v48 — Plugins, Explorer/Browser sections, Meridian FileBrowse/NetBrowse,
## input backend overhaul

- **Plugins system** (`Plugins/`, `plugin_manager.py`, `examples/`):
  auto-scanned on startup and via Settings > Plugins' Rescan button, no
  restart needed for a toggle or rescan to take effect (previously it did).
  Manifest types: `"list"` (data-driven list, own section — the bundled
  **Start** plugin pulls the Windows Start Menu in, "Run..." pinned
  first), `"webapp"` (boxes a Meridian NetBrowse instance pinned to one
  URL into its own section), and `"option"` (surfaces as a list item
  inside another section instead of getting its own). Bundled webapp
  plugins: **Telegram**, **Discord**, **Messenger**, **Snapchat**,
  **Phone Link** (Google Messages for web). `examples/BlankSection/` is a
  commented template for a new `"list"` plugin.
- **Explorer section** (right after Desktop) and **Browser section**
  (right after Explorer), both off by default. Desktop folders (now shown
  at all — previously skipped entirely) route into Explorer; internally-
  launched URLs route into Browser; both fall back through a standalone
  app then the OS default when their section is off.
- **Meridian FileBrowse** (`Meridian_FileBrowse/`) and **Meridian
  NetBrowse** (`Meridian_NetBrowse/`): separate-source-files forks of
  Meridian Explorer and CyberDeckBrowser, launched with `--box=X,Y,W,H` to
  size/position into their section's box instead of covering the screen.
  NetBrowse additionally drops the cyberpunk first-boot prompt/aesthetic
  options and gets a `--minimal-menu` mode (Y/X reduced to "Exit Program"
  only) for the Chat-section webapp plugins. Both build as single `.exe`
  files, windowed (no console).
- **System section**: Command Prompt, PowerShell, Microsoft Store,
  Windows Update.
- **Game Library**: non-big-5 platforms get their own section per
  *platform* (added a `Platform` field to the Playnite exporter) instead
  of one shared "Other" bucket; removed the Playnite filter-presets
  feature entirely per request.
- **Photos**: Start over a photo opens an Edit / Set as Background popup;
  Edit uses the file's actual default "edit" program instead of hard-
  requiring `mspaint.exe`.
- **Controller input backend overhaul**: added real **DirectInput**
  (`dinput8.dll`, custom `DIDATAFORMAT`) and **SDL3** (`SDL3.dll`) backends
  alongside GameInput/XInput. **XInput is now the default** (was
  GameInput) — Settings > Controls cycles XInput / GameInput / DirectInput
  / SDL3 / Auto, applied live. GameInput's vtable-slot-probing approach
  turned out to only reliably decode buttons, not sticks/triggers, across
  multiple independent reports, so it moved from default to opt-in.
- Onscreen-menu launching unified to always go through `osm.bat` (was
  sometimes `onscreenmenu.exe` directly) across every app that needs it.
- Dawning Horizon's open-programs bar now shrinks its height at runtime
  if a long item list would otherwise collide with it.

**Bugs found and fixed this pass** (several pre-dating this work entirely):
item-panel showing at launch before `data-radial-focus` was ever set;
`Plugins/` not found in compiled builds (PyInstaller temp-extraction
folder used instead of the real exe folder, same class of bug as GameInput
DLL path issues seen before); `osm.bat` closing onscreenmenu instead of
leaving it alone when already running; onscreenmenu's single-instance
check false-positiving against its own PyInstaller `--onefile` bootloader
process on literally every compiled launch (fine from source, where the
process is named `python.exe` and never triggers the check); a dead-code
bug in Meridian Explorer/FileBrowse where the controller's D-pad/stick/A/B
never reached the options popup at all (missing `if self.state == "menu":`
header, orphaned under the "properties" state's `continue` — keyboard
worked fine via its own, correctly-structured path); the same file's
`open_quick_access_menu()` silently no-op'ing instead of opening on an
out-of-range selection; boxed apps occasionally rendering in the wrong
place by measuring the panel's box before its slide-in transition had
actually moved it; NetBrowse's browser view not filling its window
(QWebEngineView sized before the native window was shown); NetBrowse's
build failing on `qrc_qmake_qtlabs_assetdownloader_init.cpp.obj` (a
blanket `--collect-all PySide6` pulling in unused QtQuick/QML machinery);
and a long tail of Factory Central z-index/cascade bugs — the gear
rendering translucent (glow layer sharing its z-index), decorative layers
painting above instead of behind other content (`position:fixed` +
`z-index:0` paints above normal-flow content, not below), rings not
centered on the gear (`#task-bar`'s `backdrop-filter` making it the
containing block for its own fixed-position children), the gear/sections
hugging the left edge (a base rule sets `--hub-cx`/`--hub-cy`/`--orbit-r`
directly on `#top-bar`, which silently wins over a theme's `body`-level
override of the same properties), icon/label colors drifting as the
category carousel scrolled (`:nth-of-type` counts DOM position, not
logical section identity — switched to a stable per-section index), and
clicking a section loading its content without ever opening the slide-in
panel.

## v49 — Compiled size/memory optimization

- **CyberDeckBrowser and Meridian NetBrowse** (the suite's two QtWebEngine
  apps, and by far the biggest contributors to a 2GB+ compiled size)
  switched from a blanket `--collect-all PySide6` to collecting only the
  Qt modules actually imported (QtWidgets/QtGui/QtCore/QtWebEngine*/
  QtNetwork), with ~25 unused Qt modules (QtQuick/QML, QtMultimedia,
  QtPdf, QtBluetooth, QtSql, Qt3D, QtCharts, and more — verified unused
  via a source grep first) explicitly excluded. CyberDeckBrowser
  (`--onedir`) also gets its QtWebEngine locale files trimmed to en-US
  only after building (it ships several dozen by default).
- Removed an unused `pygame` entry from CyberDeckBrowser's and Meridian
  NetBrowse's `Requirements.txt` — neither actually imports it, so it
  wasn't bloating the compiled output, just pip install time.
- **Reality check**: two Chromium-based browsers (CyberDeckBrowser and
  Meridian NetBrowse both embed QtWebEngine, which bundles a full
  Chromium build each) are inherently large — Blink/V8/GPU/codec support
  can't be excluded without breaking web rendering. This pass removes the
  *unnecessary* bloat layered on top of that unavoidable baseline; it
  won't shrink the suite to a small footprint, but should meaningfully
  reduce it. Worth measuring the actual before/after size on a real build
  to see how much this specific pass recovered.

---

## Conventions

- **Do not** modify input cooldown/debounce values unless explicitly asked.
- App data lives in `%LOCALAPPDATA%\Meridian Launcher\` with per-app subdirs.
- Build via each app's own `.bat` plus the master `CompileAndPackage.bat`.
- The two onedir apps use unique `--contents-directory` names so flat-merging
  into DskoTech doesn't collide.
- Always null-guard `el()` lookups — commented-out markup is a recurring source
  of boot-killing `TypeError`s.
- `const`/`let` used on the boot path must be declared above their first use
  (temporal dead zone has caused three separate outages).

*Vibecoded by Samuel "Zenith" Schimmel (Madisico) 2026; This is open source
software. Donations Appreciated, but Money Not Required.*

## v50 — Input backend overhaul, Carousel Deck theme, Addon Settings, plug-ons

**Input backends**
- **gameinput_native/**: a compiled pybind11 C++ extension against Microsoft's
  real, vendored GameInput SDK, replacing the old ctypes vtable-slot-guessing
  approach in `gameinput_api.py`. The real headers settled what guessing
  never could: the real `IID_IGameInput` differs from what the guessing code
  had, and the real vtable slot for `GetGamepadState` is 18, not the 22/23
  that were tried. Optional — falls back to the ctypes implementation
  automatically if the compiled `.pyd` isn't present *or* if it's present but
  fails to construct at runtime (e.g. the separate `gameinput.dll` runtime
  isn't installed) — the latter fallback path didn't exist at first and was
  a real regression versus the old code (GameInput would silently give up
  entirely instead of falling back), since fixed.
- **Browser Gamepad API** (`browser_gamepad` backend): reads the controller
  via the frontend's own `navigator.getGamepads()` instead of any native
  code at all, which has been found to keep working inside Windows' Xbox
  Full Screen Experience when the native backends don't.
- **Joy-Con Pair** (`joycon_pair` backend, experimental): combines a
  connected left + right Nintendo Joy-Con into one logical controller via
  DirectInput. Explicit opt-in only, never part of the automatic fallback
  chain — Nintendo has never published an official Joy-Con report spec, so
  the button mapping is best-effort and unverified on real hardware.
- **FSE Mode removed** — the ViGEmBus/vgamepad virtual-controller-mirroring
  approach it depended on didn't pan out in practice; superseded by Browser
  Gamepad API for the same underlying problem (Xbox FSE input reliability).
- **Controller Bridge** (`xinput_to_keyboard.py`, per-app/per-game only —
  never a global toggle): every previously-unmapped button now gets a
  default number-key (1-9) assignment instead of being left blank. Also
  picks up a `meridian_controller_bridge.json` dropped in a game/app's own
  install folder automatically (`--game-dir`), so a custom mapping no
  longer has to be hand-picked in Settings for every game that needs one -
  an explicit Settings-picked mapping still takes priority if set.

**Carousel Deck theme**
A new built-in layout (`carousel_deck`) built from a supplied diagram: a
horizontal Sections bar + battery/clock strip above a new full-width
"Screen Bar" (hosting a spinning icon for the current selection, plug-on
content, and the non-fullscreen video player — plug-ons always render here
at full size for this theme regardless of their own layout settings), then
the familiar subfolder/options/thumbnail 3-column row with the taskbar and
music player nested directly under their respective boxes instead of
floating separately. Section icons are a windowed 8-visible carousel
(others aren't hidden — they're simply not in the DOM) with directional
sliding and edge-conflict hiding against the clock/battery block.

**Addon Settings**
A new generic, scannable settings page (`addon_settings.py`): any
`Plugins/<name>/settings.json` or `themes/<name>/settings.json` describing
its own settings (toggle/choice/file/text fields) is discovered and
rendered automatically in Settings > Addon Settings — no `app.js` changes
needed for a new plugin or theme's settings to show up. Replaces an earlier
approach where a theme-specific setting (Carousel Deck's gallery grid
column count) was spliced into the Start menu, which showed it in every
theme regardless of relevance, since the Start menu has no per-theme
filtering concept.

**Plug-ons** ("addon"-type plugins — `plugin_manager.py`): add one option to
an existing built-in section's list instead of their own section, with
layout preferences (window position preset, which of subfolder/thumbnail/
clock/battery/taskbar/music-player stay visible while boxed) and
auto-disable when their target section is itself hidden. Ships with an
interactive generator (`examples/plugon_generator.py`) and five real
examples (Discord/Messenger/PhoneLink/Snapchat/Telegram, all targeting the
Chat section).

**Radial theme fixes**: the subfolder bar's grid column used to collapse
away entirely for sections with no subfolder content, which was also
shrinking the options list's own column width inconsistently between
sections — the two are unlinked now (the subfolder column always stays
reserved, filled with a customizable placeholder image when not
applicable), and gallery tiles are properly sized instead of the default
minimum packing as many small tiles as fit into an already-fixed-width
column.

**Reliability/safety fixes across the suite**: Meridian Explorer and
CyberDeckBrowser both now stop acting on controller/keyboard input while
not the OS foreground window, close onscreenmenu on regaining focus, and
signal Meridian Launcher to suspend its own controls while either has a
menu open (a shared flag file, since there's no OS-level way to make an
unrelated third-party program stop reading the same physical controller —
this only reaches the one other app actually positioned to cooperate).
Meridian Explorer also gained single-instance enforcement, an on-demand
"Controls" reference, an in-window `[X]` close box, and an
`--close-on-background` mode for ephemeral opens (e.g. a browser download's
"show in folder").

## v51 — Four new plug-ons, real Bluetooth pairing, CyberDeckBrowser fixes,
## gameinput_native diagnosis

**New plug-ons** (System/Apps/Streaming — off by default, enable from
Settings > Plugins): **Task Manager** (CPU/RAM per running app,
controller-navigable Focus/Close grid over a flat task list),
**Display & Audio** (resolution/refresh rate/HDR toggle/audio output
device, one panel), **Wi-Fi & Bluetooth** (real scan-and-pair for new
Bluetooth devices via WinRT through PowerShell, not just toggling
already-known ones; paired-device names now read from the actual
pairing database instead of PnP's often-generic FriendlyName; an
on-screen keyboard for Wi-Fi passwords), **Type from Phone** (a local
web page + QR code so a phone's own keyboard can type long
passwords/search terms instead of clicking them out on the on-screen
keyboard), and **HyperBeam** (Streaming section entry for
hyperbeam.com). Each is its own small local HTTP server
(`task_manager_server.py`, `display_audio_server.py`,
`network_pairing_server.py` + `bluetooth_pairing.py`,
`phone_type_server.py`) boxed into NetBrowse like any other addon
plug-on.

**Audio device switching** (System section, `audio_devices.py`): enumerate
and switch the default Windows playback device via pycaw's
`IPolicyConfig` wrapper (the same mechanism NirCmd/AudioDeviceCmdlets/
SoundSwitch use — there's no public supported API for this).

**Universal on-screen keyboard auto-invoke** (`onscreenmenu`,
`foreign_focus_watcher.py`): the fake cursor already worked against any
window automatically; `osk.exe` now does too, launching the instant a
non-Meridian window takes foreground focus rather than requiring the X
menu. Also detects the Secure Desktop (UAC) specifically and keeps
`osk.exe` pre-launched so Windows' own accessibility-tool carryover has
something to carry over — real OS-level limits apply here (no ordinary
app can draw its own overlay on the Secure Desktop by design), documented
plainly in the module docstring rather than oversold.

**Settings > Backup & Restore** (`backup_restore.py`): export/import
settings, selected theme, activated plugins, and custom Plugins/themes
folders as one `.zip`, with a confirmation step showing what's inside a
backup before it's applied.

**Settings > About**: full third-party attributions/licenses list for
every bundled dependency and Microsoft-redistributed runtime component.

**CyberDeckBrowser**:
- Real persistent logins: `QWebEngineProfile.defaultProfile()` was never
  given a stable org/app name, explicit storage path, or cookie policy —
  either gap alone causes "forgets I'm logged in" (unstable auto-derived
  storage location; `ForcePersistentCookies` missing means a site's own
  "forget me on window close" session-cookie flag wins, which desktop
  Chrome normally masks by treating "close the window" differently from
  "end the session").
- Streaming fixes beyond Widevine: `--ppapi-widevine-path` alongside
  `--widevine-path` (some QtWebEngine/Chromium versions still want the
  older PPAPI-based path), `--autoplay-policy=no-user-gesture-required`
  (a distinct failure mode from DRM — "loads, never plays, no error" —
  several streaming players' JS just stalls waiting for a `playing`
  event that Chromium won't fire without a real user gesture), a real
  desktop Chrome User-Agent (some sites allow-list known UA strings
  instead of testing capability), `PluginsEnabled` (Chromium's EME/
  Widevine is architecturally still a "plugin" internally).
- Per-context profile isolation: CyberDeckBrowser is deliberately
  multi-instance when boxed (Browser section + each webapp plugin get
  their own simultaneous process) — the persistent-login fix above
  initially pointed every one of them at the same shared profile path,
  which triggered Chromium's own same-profile-two-processes lock: the
  second window's Qt chrome (background, exit button) rendered fine but
  its Chromium content area stayed permanently blank. Each window now
  gets its own storage subfolder keyed by its `--notify-exit=` purpose
  (`browser`, a plugin id, or `standalone`) — stable across repeat opens
  of the same context, isolated from whatever else is open at the same
  time.
- Web section's own "CyberDeckBrowser" entry now always launches the
  program directly (`launch_cyberdeckbrowser_standalone()`) instead of
  sometimes getting routed through the URL-opening/Browser-section
  logic meant for actual links.

**gameinput_native diagnosis and fix** (the real Microsoft GameInput SDK
backend for controller input, see `gameinput_native/README.md`):
- `DIAG["native_status"]` (Settings > Controls) now always reports
  exactly why the native backend isn't active: not built, built but
  shadowed by the source folder, built against the wrong Python ABI, or
  the runtime `gameinput.dll` missing on this machine.
- `gameinput_native/build_and_deploy.py`: builds the extension and
  deploys it to every app folder that needs it in one step.
- Root cause of it silently never working even after a "successful"
  build: the PyInstaller `.spec` files never excluded `gameinput_native/`
  (the C++ source folder) from analysis, so a hollow, empty reference to
  it got baked into every frozen build — and since PyInstaller's own
  frozen importer checks that embedded reference before ever touching
  the real filesystem, the externally-placed `.pyd` was unreachable
  regardless of how correctly it was staged. Fixed with
  `excludes=['gameinput_native']` in every `.spec` file, paired with an
  explicit `sys.path` addition in `gameinput_api.py` (frozen-aware: the
  running `.exe`'s own folder) so the real file can actually be found
  once the phantom reference is gone.
- `InstallMeridianSuite_WithGameInputBuild.bat`: a separate variant of
  the main installer that additionally installs the MSVC Build Tools
  (via `vswhere`-based detection first — skips entirely, not just a
  fast no-op, if already present) and builds/stages `gameinput_native`.
  Kept as its own file rather than a flag on the main installer since
  it's a multi-GB download most people don't need.

**Crash fix**: `audio_devices.py`'s pycaw/comtypes import was an
unconditional `if IS_WINDOWS: import pycaw...` that crashed the whole
app at startup (`ModuleNotFoundError`) on any build where those weren't
actually bundled — now wrapped in try/except like every other optional
dependency in the suite, degrading to "unavailable" in the UI instead.

**Housekeeping**: `obsolete/` — files identified as superseded by later
work, quarantined rather than deleted so they can be reviewed. The
original full "Meridian NetBrowse" browser engine (superseded by
CyberDeckBrowser's `--box=` merge — only its still-used default-browser
shell-handler trampoline stays in `Meridian_NetBrowse/`), and the old
GameInput vtable-slot-guessing diagnostic tools (superseded by
`gameinput_native`, though still has some relevance to the ctypes
fallback path). See `obsolete/README.md`.
