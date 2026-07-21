"""backup_restore.py — Settings > Program > "Backup & Restore".

Bundles everything a person would expect "my Meridian Launcher setup" to
mean into one .zip: settings.json (which already contains the selected
theme/layout, custom_sections, hidden_builtin_sections, plugin visibility
flags, addon_settings, etc — see store.default_settings()), the keyboard
and controller control maps, and the actual Plugins/ and themes/ folders
next to the exe (the real files behind "activated plugins" and "custom
sections/plugins" — settings.json only stores which plugin ids are
visible, not the plugin code/manifests themselves).

Deliberately NOT included: cached thumbnails (CACHE_DIR — regenerable,
would bloat the zip for no reason) and machine-specific paths that
wouldn't make sense to carry to a different install (media folder paths,
individual .exe paths in Apps/Games/etc) are left as-is inside
settings.json rather than stripped — restoring on the SAME machine (the
common case: reinstall, move to a new drive, or just keeping a safety
copy) makes those still work; restoring onto a different machine may
need those paths re-pointed by hand afterward, same as any settings.json
copied by hand would.
"""

import json
import shutil
import tempfile
import zipfile
from pathlib import Path

import store

BACKUP_FORMAT_VERSION = 1

# Relative to BASE_DIR (the folder the app itself lives in) — the real
# on-disk folders behind "activated plugins" and "custom sections/
# plugins". Only backed up/restored if they actually exist.
_APP_DIR_FOLDERS = ["Plugins", "themes"]

# Relative to store.DATA_DIR (%LOCALAPPDATA%\Meridian Launcher\) — the
# actual settings/control files. overlay.png and theme_assets/ are left
# out on purpose: they're large, per-theme cosmetic images a person picks
# via a file dialog anyway (the picked path is what's in settings.json,
# not a managed copy), not core "settings".
_DATA_FILES = [
    store.SETTINGS_FILE,
    store.KEYBOARD_CONTROLS_FILE,
    store.CONTROLLER_CONTROLS_FILE,
]


def export_backup(base_dir: Path, dest_zip_path: str, app_version: str):
    """Writes a backup bundle to dest_zip_path. Returns {"ok": bool,
    "error": str|None}."""
    try:
        dest = Path(dest_zip_path)
        if dest.suffix.lower() != ".zip":
            dest = dest.with_suffix(".zip")
        dest.parent.mkdir(parents=True, exist_ok=True)

        with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED) as zf:
            manifest = {
                "format_version": BACKUP_FORMAT_VERSION,
                "app_version": app_version,
                "layout": store.load_settings().get("layout"),
            }
            zf.writestr("manifest.json", json.dumps(manifest, indent=2))

            for f in _DATA_FILES:
                if f.exists():
                    zf.write(f, arcname=f"data/{f.name}")

            for folder_name in _APP_DIR_FOLDERS:
                folder = base_dir / folder_name
                if not folder.is_dir():
                    continue
                for path in folder.rglob("*"):
                    if path.is_file():
                        arcname = f"appdir/{folder_name}/{path.relative_to(folder)}"
                        zf.write(path, arcname=arcname)

        return {"ok": True, "error": None}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def _read_manifest(zf: zipfile.ZipFile):
    try:
        return json.loads(zf.read("manifest.json").decode("utf-8"))
    except Exception:
        return None


def inspect_backup(zip_path: str):
    """Peek at a backup without applying it, for a confirmation prompt.
    Returns {"ok": bool, "error": str|None, "manifest": dict|None,
    "has_plugins": bool, "has_themes": bool}."""
    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            manifest = _read_manifest(zf)
            if manifest is None:
                return {"ok": False, "error": "Not a Meridian Launcher backup (missing manifest.json).",
                         "manifest": None, "has_plugins": False, "has_themes": False}
            names = zf.namelist()
            return {
                "ok": True, "error": None, "manifest": manifest,
                "has_plugins": any(n.startswith("appdir/Plugins/") for n in names),
                "has_themes": any(n.startswith("appdir/themes/") for n in names),
            }
    except Exception as e:
        return {"ok": False, "error": str(e), "manifest": None, "has_plugins": False, "has_themes": False}


def import_backup(base_dir: Path, zip_path: str):
    """Restores a backup bundle written by export_backup(). Overwrites
    settings.json/control files and merges the Plugins/themes folders
    in (restored files win on a name clash; anything currently on disk
    that isn't in the backup is left alone rather than deleted, so a
    restore never silently removes a plugin someone installed after the
    backup was made). Returns {"ok": bool, "error": str|None}.

    Extraction happens into a temp dir first and is only copied over the
    real locations once every file has unpacked successfully, so a
    corrupt/truncated zip can't leave settings half-overwritten."""
    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            manifest = _read_manifest(zf)
            if manifest is None:
                return {"ok": False, "error": "Not a Meridian Launcher backup (missing manifest.json)."}

            with tempfile.TemporaryDirectory(prefix="meridian_restore_") as tmp:
                tmp = Path(tmp)
                zf.extractall(tmp)

                data_src = tmp / "data"
                if data_src.is_dir():
                    store.DATA_DIR.mkdir(parents=True, exist_ok=True)
                    for f in data_src.iterdir():
                        if f.is_file():
                            shutil.copy2(f, store.DATA_DIR / f.name)

                appdir_src = tmp / "appdir"
                if appdir_src.is_dir():
                    for folder_name in _APP_DIR_FOLDERS:
                        src_folder = appdir_src / folder_name
                        if not src_folder.is_dir():
                            continue
                        dest_folder = base_dir / folder_name
                        dest_folder.mkdir(parents=True, exist_ok=True)
                        for path in src_folder.rglob("*"):
                            if path.is_file():
                                rel = path.relative_to(src_folder)
                                out = dest_folder / rel
                                out.parent.mkdir(parents=True, exist_ok=True)
                                shutil.copy2(path, out)

        return {"ok": True, "error": None}
    except Exception as e:
        return {"ok": False, "error": str(e)}
