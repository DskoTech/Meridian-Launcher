"""Meridian Launcher plug-on generator.

Interactive CLI that scaffolds a "plug-on" (an "addon"-type plugin, see
plugin_manager.py's module docstring) into Plugins/<name>/plugin.json,
ready for Meridian Launcher to pick up on its next plugin rescan.

A plug-on adds ONE option to an existing BUILT-IN section's list - never
its own section, and never anything outside those built-ins. This
generator specifically offers Emulators, Videos, Streaming, Chat, Games,
Web, or Apps (see BUILTIN_SECTIONS below) - the sections plug-ons are
actually meant for; Meridian Launcher's own addon validation
(plugin_manager.BUILTIN_SECTION_IDS) is broader than this curated list,
but this generator only prompts for the sections above. It shows up
after that section's own built-in entries but before any of the user's
own custom entries there (e.g. Web section shortcuts) - Meridian
Launcher handles that ordering on its own; nothing here needs to worry
about it. It's auto-disabled by Meridian Launcher whenever its target
section is itself hidden, and its enable/disable toggle lives in the
normal Settings > Plugins list alongside every other plugin - nothing
generator- or plug-on-specific there either.

WHAT THIS GENERATES TODAY
--------------------------
Only the "webapp" behavior (open a URL, boxed into the section's list
like the Browser section already boxes pages) - the only addon behavior
implemented in Meridian Launcher so far. As more addon behaviors land
(the docstring in plugin_manager.py mentions boxing an arbitrary outside
.exe that draws into the options/item window instead of a URL, for
example), this generator is meant to grow a prompt for which behavior to
scaffold, the same way it already prompts for section/name/position/
visibility - it isn't a one-shot script, it's meant to keep being the
one place that knows how to build every addon kind that exists.

USAGE
-----
    python examples/plugon_generator.py

Follow the prompts. Existing plugin ids are refused (no silent
overwrite) - remove or rename the old folder first if you want to
regenerate one.
"""

import json
import re
import sys
from pathlib import Path

# Plugins/ lives next to main.py, one level up from this examples/ folder.
BASE_DIR = Path(__file__).resolve().parent.parent
PLUGINS_DIR = BASE_DIR / "Plugins"

# Keep in sync with plugin_manager.BUILTIN_SECTION_IDS.
BUILTIN_SECTIONS = [
    ("emulators", "Emulators"), ("videos", "Videos"), ("streaming", "Streaming"),
    ("chat", "Chat"), ("games", "Games"), ("web", "Web"), ("apps", "Apps"),
]

WINDOW_POSITIONS = [
    ("default", "Default (fills the section's whole options/list box)"),
    ("centered", "Centered (70% size, centered in the box)"),
    ("left_edge_to_right_edge", "Left edge to right edge (full width, stops before the Sections bar)"),
    ("left_half", "Left half"),
    ("right_half", "Right half"),
]

VISIBILITY_TOGGLES = [
    ("show_subfolder", "Show the subfolder/filter side panel while this plug-on is open?"),
    ("show_thumbnail", "Show the large thumbnail/preview pane while this plug-on is open?"),
    ("show_clock", "Show the clock while this plug-on is open?"),
    ("show_battery", "Show the battery indicator while this plug-on is open?"),
    ("show_taskbar", "Show the open-programs taskbar while this plug-on is open?"),
    ("show_music_player", "Show the music player while this plug-on is open?"),
]


def _slugify(name):
    slug = re.sub(r"[^a-z0-9]+", "-", name.strip().lower()).strip("-")
    return slug or "plugon"


def _prompt(question, default=None):
    suffix = f" [{default}]" if default is not None else ""
    while True:
        answer = input(f"{question}{suffix}: ").strip()
        if answer:
            return answer
        if default is not None:
            return default
        print("  (required)")


def _prompt_choice(question, choices):
    print(question)
    for i, (_value, label) in enumerate(choices, 1):
        print(f"  {i}. {label}")
    while True:
        raw = input(f"Choose 1-{len(choices)}: ").strip()
        if raw.isdigit() and 1 <= int(raw) <= len(choices):
            return choices[int(raw) - 1][0]
        print("  (enter a number from the list)")


def _prompt_yes_no(question, default=True):
    suffix = " [Y/n]" if default else " [y/N]"
    while True:
        raw = input(f"{question}{suffix}: ").strip().lower()
        if not raw:
            return default
        if raw in ("y", "yes"):
            return True
        if raw in ("n", "no"):
            return False
        print("  (y or n)")


def main():
    print("Meridian Launcher plug-on generator")
    print("------------------------------------")
    print("Generates a webapp-type (open a URL) plug-on. More addon kinds")
    print("will get their own prompt here as they're added to Meridian")
    print("Launcher itself.\n")

    name = _prompt("Plug-on name (shown in Settings > Plugins)")
    plugin_id = _slugify(name)
    target_dir = PLUGINS_DIR / plugin_id
    if target_dir.exists():
        print(f"\nPlugins/{plugin_id}/ already exists - remove or rename it first, "
              "or pick a different name.")
        sys.exit(1)

    section = _prompt_choice("\nWhich built-in section should this option appear in?", BUILTIN_SECTIONS)
    option_label = _prompt("\nOption label (shown as the list entry's text)", default=name)
    url = _prompt("\nURL to open")

    window_position = _prompt_choice("\nWindow position for the boxed page:", WINDOW_POSITIONS)

    print("\nLayout while this plug-on is open (defaults to yes/shown for all):")
    layout = {"window_position": window_position}
    for key, question in VISIBILITY_TOGGLES:
        layout[key] = _prompt_yes_no(f"  {question}", default=True)

    manifest = {
        "id": plugin_id,
        "label": name,
        "type": "addon",
        "section": section,
        "option": option_label,
        "url": url,
        **layout,
    }

    target_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = target_dir / "plugin.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    print(f"\nWrote {manifest_path}")
    print("It'll show up in Settings > Plugins (off by default, same as every "
          "other plugin) the next time Meridian Launcher starts, or immediately "
          "if you use the \"Rescan Plugins\" button there.")
    print(f"It'll appear in the {dict(BUILTIN_SECTIONS)[section]} section's list "
          "once enabled there - unless that section is itself hidden, in which "
          "case it stays auto-disabled until the section is shown again.")


if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, EOFError):
        print("\nCancelled.")
