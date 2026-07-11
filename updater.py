"""
Update checking + self-update for Meridian Launcher, against GitHub
Releases at https://github.com/DskoTech/Meridian-Launcher/releases/.

Uses only the standard library (urllib, json, tempfile, subprocess) — no
extra dependency.

Release asset convention this expects: the latest GitHub release should
have an installer attached named exactly "MeridianLauncher" followed by its
version number and ".exe" — e.g. "MeridianLauncher1.0.1.exe" (an Inno
Setup/NSIS/etc installer that knows how to update an existing install in
place). The release may also carry other .exe assets (e.g.
Meridian.Exporter.exe, a separate Playnite extension installer) — those are
matched by name and skipped, never downloaded or run by this module. This
just finds the one installer that matches, downloads it, and launches it;
the installer itself is responsible for everything after that (closing/
waiting out a running MeridianLauncher.exe if it needs to, overwriting
files, relaunching, etc).

The release's tag name is compared against the local VERSION file using
simple dotted-numeric version comparison (e.g. "v1.2.0" > "v1.1.9"); tags
that don't look like a version at all are just never treated as an update.
"""

import json
import os
import re
import subprocess
import tempfile
import urllib.error
import urllib.parse
import urllib.request

GITHUB_API_LATEST_RELEASE = (
    "https://api.github.com/repos/DskoTech/Meridian-Launcher/releases/latest"
)
GITHUB_RELEASES_PAGE = "https://github.com/DskoTech/Meridian-Launcher/releases/"

USER_AGENT = "MeridianLauncher-UpdateChecker"

# The release also ships a second installer, Meridian.Exporter.exe (a
# Playnite extension installer, unrelated to Meridian Launcher itself) —
# both assets have "meridian" in the name, so matching on that alone would
# risk grabbing the wrong one. The actual app installer is always named
# "MeridianLauncher" immediately followed by its version number and
# ".exe", e.g. "MeridianLauncher1.0.1.exe" — matched exactly, so
# Meridian.Exporter.exe (and anything else) is never mistaken for it.
MAIN_INSTALLER_NAME_RE = re.compile(r"^meridianlauncher[\d.]*\.exe$", re.IGNORECASE)


def _parse_version(v):
    """'v1.2.3' / '1.2.3' -> (1, 2, 3). Anything that doesn't look like a
    dotted numeric version falls back to (0,), so a weird/non-version tag
    on the release never crashes the comparison — it's just treated as
    "not newer" rather than raising."""
    v = (v or "").strip()
    if v.lower().startswith("v"):
        v = v[1:]
    parts = []
    for chunk in v.split("."):
        digits = "".join(ch for ch in chunk if ch.isdigit())
        if not digits:
            return (0,)
        parts.append(int(digits))
    return tuple(parts) if parts else (0,)


def is_newer(remote_version, local_version):
    return _parse_version(remote_version) > _parse_version(local_version)


def get_local_version(version_file_path):
    try:
        with open(version_file_path, "r", encoding="utf-8") as f:
            return f.read().strip() or "0.0.0"
    except OSError:
        return "0.0.0"


def check_for_update(current_version, timeout=6):
    """Hits the GitHub API once. Returns a dict:
      {"available": bool, "current": str, "latest": str,
       "download_url": str|None, "notes": str, "error": str|None}

    Never raises — network failures, GitHub rate limiting, and a repo with
    no releases published yet are all reported back as a plain dict with an
    "error" string instead of an exception, since this runs silently in the
    background at boot and a failed check should just be quietly ignored,
    not crash the app.
    """
    result = {
        "available": False,
        "current": current_version,
        "latest": current_version,
        "download_url": None,
        "notes": "",
        "error": None,
    }

    req = urllib.request.Request(
        GITHUB_API_LATEST_RELEASE,
        headers={"Accept": "application/vnd.github+json", "User-Agent": USER_AGENT},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        result["error"] = "No releases published yet." if e.code == 404 else f"GitHub returned HTTP {e.code}."
        return result
    except Exception as e:
        result["error"] = f"Couldn't reach GitHub: {e}"
        return result

    latest_tag = data.get("tag_name") or ""
    result["latest"] = latest_tag or current_version
    result["notes"] = (data.get("body") or "").strip()

    assets = data.get("assets") or []
    exe_assets = [a for a in assets if (a.get("name") or "").lower().endswith(".exe")]
    if exe_assets:
        # Only ever match the main app installer by its exact naming
        # convention (MeridianLauncher#.#.#.exe) — never falls back to
        # "any .exe attached to the release", since that release also
        # includes Meridian.Exporter.exe (a separate, unrelated installer)
        # which must never be downloaded and run here by mistake.
        preferred = next(
            (a for a in exe_assets if MAIN_INSTALLER_NAME_RE.match((a.get("name") or "").strip())),
            None,
        )
        if preferred:
            result["download_url"] = preferred.get("browser_download_url")

    if latest_tag and is_newer(latest_tag, current_version):
        if result["download_url"]:
            result["available"] = True
        else:
            result["error"] = "A newer version is out, but it has no .exe installer attached to download."

    return result


def _download(url, dest_path, timeout=30, on_progress=None):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as resp, open(dest_path, "wb") as out:
        total = int(resp.headers.get("Content-Length") or 0)
        read = 0
        while True:
            chunk = resp.read(1 << 16)
            if not chunk:
                break
            out.write(chunk)
            read += len(chunk)
            if on_progress and total:
                try:
                    on_progress(read, total)
                except Exception:
                    pass


def download_and_run_installer(download_url, on_progress=None):
    """Downloads the release's .exe installer to a temp folder and launches
    it. Returns (ok, error_message) for the download/launch step only — the
    actual install happens inside the installer itself, which runs as its
    own separate process.

    The caller is expected to quit the app right after this returns
    (ok=True): most installers (Inno Setup, NSIS, etc.) either can't
    overwrite a running MeridianLauncher.exe, or will prompt/wait to close
    it themselves — either way, getting out of the installer's way
    immediately is the safest bet rather than assuming any particular
    installer's behavior.
    """
    try:
        tmp_dir = tempfile.mkdtemp(prefix="meridian_update_")
        url_name = os.path.basename(urllib.parse.urlparse(download_url).path)
        installer_name = url_name if url_name.lower().endswith(".exe") else "MeridianLauncherSetup.exe"
        installer_path = os.path.join(tmp_dir, installer_name)

        _download(download_url, installer_path, on_progress=on_progress)

        subprocess.Popen([installer_path], cwd=tmp_dir, close_fds=True)
        return True, None
    except Exception as e:
        return False, str(e)
