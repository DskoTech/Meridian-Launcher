# Features

What the Meridian suite actually does, app by app and section by section.
For controls, see **CONTROLS_README.txt**. For themes/settings/Plugins,
see **CUSTOMIZATION.md**. For version history, see **CHANGELOG.md**.

## Meridian Launcher

The front end of the suite: one horizontal row of sections, a vertical
list per section, navigable by controller, keyboard, or mouse.

### Sections

| Section | What it is | Default |
|---|---|---|
| Music / Photos / Videos | Media libraries, scanned from folders you point it at | on |
| Apps / Games / Emulators / Chat / Streaming | Custom launchable lists (exe/bat/shortcuts), plus any option-type plugins targeting that section | on |
| Web | Launch CyberDeckBrowser, or web shortcuts you've added | on |
| Desktop | Whatever's actually on your Windows Desktop right now — files, folders, shortcuts | **off** |
| Explorer | Boxes Meridian FileBrowse; Desktop folders open here when it's on | **off** |
| Browser | Boxes Meridian NetBrowse; internally-launched URLs open here when it's on | **off** |
| Plugins (Start, Telegram, Discord, Messenger, Snapchat, Phone Link, Task Manager, Display & Audio, Wi-Fi & Bluetooth, Type from Phone, HyperBeam, anything you drop into `Plugins/`) | See below | **off** (each individually) |
| Settings / System (incl. Audio Output device switching) | The app's own controls | on (hidden in kiosk mode) |

Every section's presence, and most of their behavior, is a Settings
toggle — nothing here is permanent.

### Embedded apps (Explorer / Browser / webapp plugins)

Instead of a plain list, these sections box a real sub-application into
the section's own list-frame area:

- **Explorer** boxes **Meridian FileBrowse** (a full dual-pane file
  manager — copy/cut/paste/rename/delete/multi-select/undo-redo, a
  built-in text and hex editor, view modes, sort, search, a Quick Access
  rail).
- **Browser** boxes **Meridian NetBrowse** (a full web browser — tabs,
  history, downloads, bookmarks, find-in-page, a virtual mouse and
  on-screen keyboard for gamepad-only use).
- **Webapp plugins** (Telegram, Discord, Messenger, Snapchat, Phone Link,
  or any you add) box the same Meridian NetBrowse engine, pinned to one
  site, with the menus stripped down to just "Exit Program."

All of these are genuinely separate processes, sized/positioned into the
section's box rather than covering the screen, and they hand focus and
controls back to Meridian Launcher automatically the moment they close —
you don't do anything extra.

### Plugins

A `Plugins/` folder next to the exe. Anything in it with a valid
`plugin.json` shows up in Settings > Plugins (hidden by default; toggle
it on, no restart needed). Four kinds:

- **`"list"`** — a plain data-driven list, gets its own section. The
  bundled example is **Start**: your Windows Start Menu, with "Run..."
  pinned at the top.
- **`"webapp"`** — boxes Meridian NetBrowse pinned to one URL, gets its
  own section. The bundled examples are Telegram, Discord, Messenger,
  Snapchat, and Phone Link.
- **`"option"`** — doesn't get its own section; shows up as an item
  inside whichever section its manifest points at instead (e.g. several
  chat apps all living inside one "Chat" section as options rather than
  five separate sections).
- **`"addon"`** — like `"option"`, splices one entry into an existing
  built-in section instead of getting its own, with layout preferences
  (window position, which of subfolder/thumbnail/clock/battery/taskbar/
  music-player stay visible while boxed) and auto-disable when its
  target section is itself hidden. Bundled examples: **Task Manager**
  and **Display & Audio** and **Wi-Fi & Bluetooth** (System section),
  **Type from Phone** (Apps section), **HyperBeam** (Streaming section)
  — each runs its own small local web server (see each `*_server.py`'s
  module docstring) rather than pointing at an external site.

See **CUSTOMIZATION.md** for how to write your own.

### Controller input

Four backends: **XInput** (default — the plain, stable, fully-public
Windows API), **GameInput** (Microsoft's modern replacement, adds
Guide-button reporting, but has had reliability issues with sticks/
triggers on real hardware), **DirectInput** (for older/exotic controllers
XInput doesn't recognize), and **SDL3** (needs `SDL3.dll` present).
Settings > Controls has a one-button cycle between them, applied live.

### Kiosk mode

A real lock, not just a window style. Turning it on shows a confirmation
that discloses all three ways back out, then Settings and System vanish
from the section row entirely. Ways out: hand-edit `window_mode` in
`settings.json`, hold Y for 45 seconds, or the D-pad/keyboard unlock code
(Up Up Down Down Left Right Left Right B A).

### Themes

Ships with several built-in layouts (CyberRadial and its variants) plus
drop-in user themes in `themes/` — pure CSS/JSON, auto-scanned at
startup, no code required. See **CUSTOMIZATION.md**.

## Meridian Game Library

A Playnite-backed (or Heroic-backed) game library front end: Steam, GOG,
Epic, and Amazon/Luna each get a dedicated section; everything else gets
one section per *platform* (PC, PlayStation, Switch, whatever Playnite
has it tagged as) instead of one shared "Other" bucket. Hide/unhide/rename
titles, a Start-menu button for those actions plus quick program-close,
full window-mode parity with the Launcher.

## Meridian Explorer / Meridian FileBrowse

A dual-pane, gamepad-first file manager. Copy/cut/paste/rename/delete,
multi-select, undo/redo, a built-in text editor and hex editor (each with
their own on-screen keyboard), View/Sort/Search, a Quick Access rail
(This PC, user folders, drives, your own shortcuts), Set as Background for
images. FileBrowse is the same app, forked into its own source files and
always launched boxed by Meridian Launcher's Explorer section rather than
full-screen.

## CyberDeckBrowser (a.k.a. "Meridian NetBrowse" when boxed)

A full gamepad-first web browser (PySide6/QtWebEngine): tabs, history,
downloads, bookmarks, find-in-page, translate, a virtual mouse (left
stick moves it, triggers boost its speed) and an on-screen keyboard that
appears automatically in text fields. One engine, not two: what used to
be a separate forked app ("Meridian NetBrowse") is now the same
`CyberDeckBrowser.exe`, launched with a `--box=X,Y,W,H` argument that
sizes/positions it into a section's list-frame box instead of covering
the screen, and skips the cyberpunk first-boot prompt/effects for that
run — Meridian Launcher's Browser section and each webapp plugin
(Telegram, Discord, etc.) each get their own simultaneous boxed
instance this way, each with its own isolated login/cookie storage so
they don't share sessions with each other or with standalone use.
Standalone CyberDeckBrowser (no `--box=`) behaves exactly as a normal
browser: full cyberpunk prompt/effects, full menus, tabs visible;
`--minimal-menu` (used for pinned-to-one-site webapp plugins) reduces
its menus to "Exit Program" only. Persistent logins, Widevine DRM
detection, and streaming-autoplay/User-Agent fixes are all configured
before any page can load — see `main.py`'s
`_configure_persistent_web_profile`/`_configure_streaming_playback` for
the specifics.

## onscreenmenu

A transparent, always-on-top controller overlay: a shortcuts menu, a key-
combo menu, a recent-apps switcher, hibernate/resume. The fake cursor
works against any window automatically, no button press needed; the
on-screen keyboard (`osk.exe`) now does too — it opens the instant a
non-Meridian window (a third-party installer, anything Meridian doesn't
know about) takes foreground focus, not just from the X menu or when
`osm.bat` launches it ahead of a native Windows dialog. Real OS-level
limits still apply to actual UAC/Secure Desktop prompts specifically —
see `onscreenmenu/features/foreign_focus_watcher.py`'s docstring for
exactly what is and isn't achievable there and why.

## Meridian_Exporter

A Playnite extension: exports your Playnite library (including each
game's platform) to a JSON file Meridian Game Library reads, and can
register itself to re-export automatically on every Playnite library
sync.
