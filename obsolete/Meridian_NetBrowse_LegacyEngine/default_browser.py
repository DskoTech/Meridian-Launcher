"""
default_browser.py — register/unregister Meridian NetBrowse as a handler for
web links, so system URL calls (default-browser opens, other apps' "open
in browser") route to it.

All keys are under HKCU\\Software\\Classes and HKCU\\...\\Registered
applications — current user, no admin, reversible. Windows-only; no-ops
elsewhere.

Note: Windows 10/11 guards the *default* http/https association behind a
user confirmation in Settings (the "how do you want to open this" dialog),
so this registers Meridian NetBrowse as an available, fully-capable browser choice
and sets the ProgId associations it can set without elevation. Making it
THE default is then one click in Settings > Default apps (or the prompt
Windows shows). The MeridianExporter-style silent takeover of the default
isn't possible without tripping Windows' protection, by design.
"""

import os
import sys

IS_WINDOWS = sys.platform == "win32"

if IS_WINDOWS:
    import winreg

PROGID = "MeridianNetBrowseHTML"
APPREG = "MeridianNetBrowse"


def _set(root, path, value, name=None, vtype=None):
    key = winreg.CreateKey(root, path)
    try:
        winreg.SetValueEx(key, name, 0, vtype or winreg.REG_SZ, value)
    finally:
        winreg.CloseKey(key)


def _delete_tree(root, path):
    try:
        key = winreg.OpenKey(root, path, 0, winreg.KEY_READ | winreg.KEY_WRITE)
    except OSError:
        return
    try:
        while True:
            try:
                sub = winreg.EnumKey(key, 0)
            except OSError:
                break
            _delete_tree(root, path + "\\" + sub)
        winreg.CloseKey(key)
        winreg.DeleteKey(root, path)
    except OSError:
        pass


def is_registered():
    if not IS_WINDOWS:
        return False
    try:
        winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                       r"Software\Classes\%s" % PROGID).Close()
        return True
    except OSError:
        return False


def register(exe_path):
    """Register Meridian NetBrowse as a capable browser and associate the http/https/
    ftp/file ProgIds and .htm/.html files with it, for the current user."""
    if not IS_WINDOWS:
        return False, "Windows only.", False
    try:
        H = winreg.HKEY_CURRENT_USER
        cmd = '"%s" "%%1"' % exe_path
        # ProgId: how to open this class of link
        _set(H, r"Software\Classes\%s" % PROGID, "Meridian NetBrowse Document")
        _set(H, r"Software\Classes\%s\DefaultIcon" % PROGID, '"%s",0' % exe_path)
        _set(H, r"Software\Classes\%s\shell\open\command" % PROGID, cmd)

        # Capabilities block so Meridian NetBrowse shows up in Settings > Default apps
        capbase = r"Software\MeridianNetBrowse\Capabilities"
        _set(H, capbase, "Meridian NetBrowse", "ApplicationName")
        _set(H, capbase, "Gamepad-first cyberpunk web browser", "ApplicationDescription")
        for scheme in ("http", "https", "ftp"):
            _set(H, capbase + r"\URLAssociations", PROGID, scheme)
        for ext in (".htm", ".html"):
            _set(H, capbase + r"\FileAssociations", PROGID, ext)
        # advertise the capabilities to Windows
        _set(H, r"Software\RegisteredApplications", capbase,
             APPREG)

        # Also point the per-user UrlAssociations UserChoice-adjacent
        # ProgId defaults we're allowed to set (best-effort; Windows may
        # still require the user to confirm the default).
        for scheme in ("http", "https"):
            try:
                _set(H, r"Software\Classes\%s\shell\open\command" % scheme, cmd)
            except Exception:
                pass

        return True, None, True
    except Exception as e:
        return False, str(e), False


def unregister():
    if not IS_WINDOWS:
        return False, "Windows only."
    try:
        H = winreg.HKEY_CURRENT_USER
        _delete_tree(H, r"Software\Classes\%s" % PROGID)
        _delete_tree(H, r"Software\MeridianNetBrowse")
        try:
            key = winreg.OpenKey(H, r"Software\RegisteredApplications", 0,
                                 winreg.KEY_READ | winreg.KEY_WRITE)
            try:
                winreg.DeleteValue(key, APPREG)
            except OSError:
                pass
            finally:
                winreg.CloseKey(key)
        except OSError:
            pass
        return True, None
    except Exception as e:
        return False, str(e)
