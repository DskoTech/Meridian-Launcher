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
