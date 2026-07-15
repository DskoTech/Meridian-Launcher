"""Meridian Launcher — Blank Section plugin template.

HOW TO USE THIS TEMPLATE
-------------------------
1. Copy this whole "BlankSection" folder into the Plugins/ directory next
   to Meridian Launcher's main.py.
2. Rename the folder to whatever you like, and change "id" and "label" in
   plugin.json to match. "id" must be unique among all sections.
3. Fill in list_items() and activate_item() below.
4. Launch Meridian Launcher (or use the "Rescan Plugins" button in
   Settings > Plugins) — your section appears in the sections bar, hidden
   by default. Enable it from Settings > Plugins.

TWO KINDS OF PLUGIN
--------------------
Most plugins are simple LIST plugins: list_items() returns a flat list of
{"id", "label", "icon"} the user can navigate up/down and press A to run,
exactly like the built-in Apps/Games sections. Meridian Launcher's normal
list navigation and normal Exit-to-sections-bar behavior handles all of
this for you automatically — you only need list_items()/activate_item().
The "Start" plugin (Plugins/Start/) is an example of this simpler kind,
and needs no special control hand-off at all.

The other kind EMBEDS a whole sub-application inside the section's box
(the way Meridian FileBrowse and Meridian NetBrowse embed a file browser
/ web browser inside the Explorer / Browser sections). That's a much
bigger undertaking outside the scope of this template — see how
Meridian FileBrowse hooks into main.py/app.js for the pattern:
  - on load (A button from the sections bar): Meridian Launcher's own
    keyboard/controller control bindings are deactivated, and the
    plugin's own control bindings take over, with the plugin's internal
    UI receiving focus.
  - the plugin's own "close program" style actions are relabeled
    "Exit Program", and instead of closing anything, they move the
    selector back to the sections bar, restore Meridian Launcher's
    control bindings, and deactivate the plugin's control bindings.
  - when the user switches to a different section, the embedded plugin
    is unloaded (not left running in the background).
This template intentionally does NOT implement that heavier pattern —
it's here as a pointer for advanced plugin authors, not something every
plugin needs.

BASIC NAV / EXIT (what this template actually provides)
---------------------------------------------------------
Because this is a plain list plugin, "navigation" is just the normal
list controls Meridian Launcher already gives every section for free:
  Keyboard : Up/Down arrows move the highlight, Enter confirms
             (calls activate_item), Space/Back returns to the sections
             bar (no plugin-specific code needed for either).
  Controller: D-pad/left stick up/down moves the highlight, A confirms
             (calls activate_item), B returns to the sections bar.
There is no "Exit Program" button to wire up here, because a list
plugin never captures input the way an embedded app does — Back/B
always simply backs out to the sections bar, same as any other section.
"""


def list_items():
    """Return the list shown in this section's box.

    Each item is a dict:
      {"id": "unique-string", "label": "Shown to the user", "icon": "app"}

    "icon" is optional; it looks up the same icon set Meridian Launcher
    already uses elsewhere (e.g. "app", "folder", "run"). Omit it to fall
    back to a generic icon.
    """
    return [
        # Example placeholder rows — replace with real data.
        # {"id": "example_1", "label": "Example Item 1", "icon": "app"},
        # {"id": "example_2", "label": "Example Item 2", "icon": "app"},
    ]


def activate_item(item_id):
    """Called when the user presses A / Enter on an item returned above.

    Must return {"ok": True, "error": None} on success, or
    {"ok": False, "error": "message shown in a toast"} on failure.
    """
    return {"ok": False, "error": f"No action wired up yet for '{item_id}'."}
