# Customization

Everything here is done without touching the app's own code — themes are
plain CSS/JSON, plugins are small Python files with a JSON manifest, and
almost every behavior is a Settings toggle. All settings live in
`settings.json` under `%LOCALAPPDATA%\Meridian Launcher\` and each app's
own subfolder there.

## Settings

Nearly everything mentioned in FEATURES.md is a Settings toggle, off by
default unless noted:

- **Sections**: Desktop (on by default), Explorer, Browser — each its own
  toggle. When Explorer or Browser is off, its fallback chain (standalone
  app, then the OS default) is what handles the same click/link instead.
- **Plugins**: Settings > Plugins lists everything discovered in
  `Plugins/`, each with its own show/hide toggle, plus a Rescan button.
  Toggling or rescanning updates the sections bar immediately.
- **Onscreen-menu integration**: a per-section "Launch with onscreenmenu?"
  toggle, plus a global "Launch External System features with
  onscreenmenu?" one for the System section. Both route through
  `osm.bat`, which only launches `onscreenmenu.exe` if it isn't already
  running — it won't close an already-open one.
- **Controller input backend**: Settings > Controls, a cycle button
  (XInput / GameInput / DirectInput / SDL3 / Auto).
- **Kiosk mode**: Settings, behind a confirmation that explains how to
  get back out before you turn it on.
- **Foreground trigger**, **close-tasks-without-prompt**, **auto-shuffle
  songs**, custom section colors, background images per theme, and more
  — browse Settings for the full list; each has its own on-screen
  description of what it currently does.

## Themes

`themes/<Theme Name>/theme.css` (+ an optional `theme.json` naming it and
picking a `"base"` layout to inherit from) — dropped into that folder and
auto-scanned at startup, no rescan or restart needed to appear in the
theme picker. A theme is CSS scoped under `body.layout-user-<slug>`,
layered on top of whichever base layout (`cyber_radial` and its variants)
it declares.

If you're writing one, a few things worth knowing from hard-won
experience with the bundled themes:

- **Custom properties declared directly on an element beat ones merely
  inherited from an ancestor**, even if your theme's own override sits on
  `body`. If a base layout rule sets something like `--hub-cx` directly
  on `#top-bar` itself, your `body.layout-user-yourtheme { --hub-cx: ... }`
  override needs to *also* target `#top-bar` (or whatever element the
  base rule targets) directly — setting it only on `body` won't reach
  through.
- **`position: fixed` elements with `z-index: 0` (or unset) still paint
  above ordinary in-flow content**, not below. If you want a decorative
  layer to sit strictly behind real content, give it a negative
  `z-index`, not just a low one.
- **`backdrop-filter` (like `transform`) makes an element the containing
  block for its own `position: fixed` children.** If you're hanging a
  decorative pseudo-element off an element that has `backdrop-filter` set
  anywhere in the base stylesheet, it'll be positioned relative to that
  element's own box, not the viewport — pick a different host, or one
  without that property.
- **Don't key per-item styling off `:nth-of-type`/`:nth-child`** if the
  row/list your theme is styling only mounts a moving *window* of
  elements (the section carousel does this) — position in the DOM drifts
  as the window slides, so colors/styles keyed off it will drift and
  repeat unpredictably. Use a stable identifier instead (Meridian
  Launcher sets a `--cat-idx` custom property per section, driven by its
  logical position, not DOM position — themes can key off that with
  `hue-rotate()`/`calc()` instead of `:nth-of-type`).

## Plugins

A folder under `Plugins/` (next to the exe) with a `plugin.json` manifest
is all it takes. Two files, minimum:

```
Plugins/
  YourPlugin/
    plugin.json
    backend.py       (only for "list"-type plugins)
```

### `plugin.json`

```json
{
  "id": "your_plugin",
  "label": "Your Plugin",
  "version": "1.0",
  "type": "list",
  "description": "One line shown in Settings > Plugins."
}
```

- `"type"`: `"list"` (default), `"webapp"`, `"option"`, or `"addon"`.
- `"list"` plugins also need a `backend.py` (see below).
- `"webapp"` plugins need a `"url"` field instead — no `backend.py`
  needed; Meridian Launcher boxes a Meridian NetBrowse instance pinned to
  that URL for you.
- `"option"` plugins need `"url"` (same as webapp) plus `"section"` (which
  existing section id it should surface inside, e.g. `"chat"`) — it
  behaves like a webapp plugin once activated, just without getting its
  own entry in the sections bar.
- `"addon"` plugins are like `"option"` (need `"url"` + `"section"`,
  target must be a built-in section id), with two differences: they
  auto-disable themselves when their target section is itself hidden in
  Settings, and they accept extra layout-preference fields —
  `"window_position"` (a preset, or `"default"`) and booleans
  `"show_subfolder"`/`"show_thumbnail"`/`"show_clock"`/`"show_battery"`/
  `"show_taskbar"`/`"show_music_player"` controlling which of those stay
  visible while this plugin is boxed. `"url"` doesn't have to be an
  external site — several bundled examples (Task Manager, Display &
  Audio, Wi-Fi & Bluetooth, Type from Phone) point at
  `http://127.0.0.1:<port>/`, a tiny local HTTP server the plugin starts
  itself (see e.g. `task_manager_server.py`) rather than anything on the
  open internet. That pattern is worth copying for any plugin that needs
  real logic behind it instead of just embedding an existing website.

### `backend.py` (list-type plugins only)

Two functions:

```python
def list_items():
    """Return the rows shown in this section's list."""
    return [
        {"id": "example_1", "label": "Example Item 1", "icon": "app"},
    ]

def activate_item(item_id):
    """Called when the user presses A/Enter on a row.
    Return {"ok": True, "error": None} or {"ok": False, "error": "..."}."""
    return {"ok": False, "error": f"No action wired up for '{item_id}'."}
```

That's the entire contract — Meridian Launcher's normal list navigation
(up/down + A, no controller/keyboard hand-off needed) handles everything
else. See `examples/BlankSection/` for a fully-commented starting point,
and `Plugins/Start/` for a real, working example (it lists your Windows
Start Menu, with a "Run..." entry pinned first).

Your plugin's `backend.py` is loaded as an isolated module — it never
gets merged into Meridian Launcher's own code, and stays in its own
folder/files.

## Custom sections (Apps / Games / Emulators / Chat / Streaming)

Each of these is a plain list you populate yourself from Settings — point
it at `.exe`/`.bat` files or shortcuts, give each a display name, and
they show up in that section's list. No plugin needed for this; it's
built into the app directly.

## Building a custom Windows shell replacement

`MakeUnmakeShell.ps1` can register Meridian Launcher (or Meridian
FileBrowse/NetBrowse via their own shell-handler trampolines) as the
default handler for a given action — folder opens, or the system web
browser — from Settings > Macros, once the relevant trampoline exe has
been built. See CHANGELOG.md for exactly what each one does.
