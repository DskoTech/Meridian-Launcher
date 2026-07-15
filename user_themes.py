"""
user_themes.py — discovery and loading of user-supplied custom themes.

A custom theme is a folder (or a lone .css file) inside the `themes/`
directory that sits next to the app. The simplest possible theme is:

    themes/
      MyTheme/
        theme.css          <- required: the stylesheet
        theme.json         <- optional: {"name": "...", "base": "cyber_radial"}
        preview.png        <- optional: shown in the picker (not yet used)

Or even simpler, a bare file: `themes/MyTheme.css`.

How it works at runtime:
  * Each theme gets a slug (its folder/file name, sanitized) and a body
    class `layout-user-<slug>`.
  * The frontend adds that class AND the chosen base layout's class, so a
    custom theme starts from one of the three built-ins (dawning_horizon /
    night_horizon / cyber_radial) and overrides from there. This means a
    user only has to write the CSS for what they want to *change*.
  * The theme's CSS text is handed to the frontend, which injects it into a
    <style id="user-theme-css"> element — no stylesheet files are modified.

Nothing here is destructive or trusted-code: it only ever reads .css/.json
text. A malformed theme is skipped rather than crashing discovery.
"""

import json
import re
from pathlib import Path

THEME_DIRNAME = "themes"
_VALID_BASES = ("dawning_horizon", "night_horizon", "cyber_radial")


def _slugify(name):
    """A DOM/CSS-class-safe slug from a theme's folder or file name."""
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", name.strip().lower()).strip("-")
    return slug or "theme"


def themes_dir(base_dir):
    """The themes/ folder next to the app. Created if missing so users have
    an obvious place to drop themes into."""
    d = Path(base_dir) / THEME_DIRNAME
    try:
        d.mkdir(parents=True, exist_ok=True)
        _write_readme(d)
    except OSError:
        pass
    return d


def _write_readme(d):
    readme = d / "README.txt"
    if readme.exists():
        return
    try:
        readme.write_text(
            "Drop custom themes here.\r\n\r\n"
            "A theme is either:\r\n"
            "  - a folder with a theme.css inside (plus optional theme.json), or\r\n"
            "  - a single .css file (e.g. MyTheme.css).\r\n\r\n"
            "theme.json (optional) can set:\r\n"
            '  { \"name\": \"My Cool Theme\", \"base\": \"cyber_radial\" }\r\n\r\n'
            "\"base\" is which built-in theme yours starts from and overrides:\r\n"
            "dawning_horizon, night_horizon, or cyber_radial.\r\n"
            "Your CSS is layered on top of the base, so you only need to write\r\n"
            "the rules you want to change. Target the body class\r\n"
            "  body.layout-user-<your-theme-slug>\r\n"
            "for rules that should only apply to your theme.\r\n",
            encoding="utf-8",
        )
    except OSError:
        pass


def _read_manifest(folder):
    """Parse an optional theme.json, tolerating a missing/broken file."""
    manifest = folder / "theme.json"
    data = {}
    if manifest.is_file():
        try:
            data = json.loads(manifest.read_text(encoding="utf-8-sig"))
            if not isinstance(data, dict):
                data = {}
        except (OSError, json.JSONDecodeError):
            data = {}
    return data


def discover_themes(base_dir):
    """Return a list of user themes found in themes/.

    Each theme is a dict:
        {
          "slug": "mytheme",           # DOM/CSS-class-safe id
          "name": "My Theme",          # display name
          "base": "cyber_radial",      # built-in layout to start from
          "layout": "user-mytheme",    # value stored in settings["layout"]
          "css": "<stylesheet text>",  # injected verbatim by the frontend
        }
    Malformed or unreadable entries are skipped.
    """
    out = []
    root = themes_dir(base_dir)
    if not root.is_dir():
        return out

    seen = set()
    for entry in sorted(root.iterdir(), key=lambda p: p.name.lower()):
        css_path = None
        manifest = {}
        display = None

        if entry.is_dir():
            candidate = entry / "theme.css"
            if not candidate.is_file():
                # accept the first .css in the folder as a convenience
                css_files = sorted(entry.glob("*.css"))
                candidate = css_files[0] if css_files else None
            if candidate is None:
                continue
            css_path = candidate
            manifest = _read_manifest(entry)
            display = manifest.get("name") or entry.name
            slug = _slugify(entry.name)
        elif entry.is_file() and entry.suffix.lower() == ".css":
            css_path = entry
            display = entry.stem
            slug = _slugify(entry.stem)
        else:
            continue

        if slug in seen:
            continue
        try:
            css_text = css_path.read_text(encoding="utf-8-sig")
        except OSError:
            continue

        base = manifest.get("base")
        if base not in _VALID_BASES:
            base = "dawning_horizon"

        seen.add(slug)
        out.append({
            "slug": slug,
            "name": display,
            "base": base,
            "layout": "user-" + slug,
            "css": css_text,
        })
    return out


def get_theme(base_dir, layout_value):
    """Look up a single discovered theme by its settings layout value
    ("user-<slug>"). Returns the theme dict or None."""
    if not layout_value or not layout_value.startswith("user-"):
        return None
    slug = layout_value[len("user-"):]
    for t in discover_themes(base_dir):
        if t["slug"] == slug:
            return t
    return None
