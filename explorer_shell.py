"""
explorer_shell.py — the registry side of Meridian Explorer's Windows
shell integration, as callable functions for the Launcher's Macros
section (the same operations MeridianExplorerShellIntegration.bat offers
interactively, minus the console menu).

Everything lives under HKCU\\Software\\Classes — current user only, no
Administrator needed, fully reversible. Windows-only; every function is a
safe no-op elsewhere.
"""

import sys

IS_WINDOWS = sys.platform == "win32"

if IS_WINDOWS:
    import winreg

_VERB = "MeridianExplorer"
_KEYS = (
    r"Software\Classes\Directory\shell",
    r"Software\Classes\Drive\shell",
)
_BG_KEY = r"Software\Classes\Directory\Background\shell"


def _set(path, value, name=None):
    key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, path)
    try:
        winreg.SetValueEx(key, name, 0, winreg.REG_SZ, value)
    finally:
        winreg.CloseKey(key)


def _delete_tree(path):
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, path, 0,
                             winreg.KEY_READ | winreg.KEY_WRITE)
    except OSError:
        return
    try:
        while True:
            try:
                sub = winreg.EnumKey(key, 0)
            except OSError:
                break
            _delete_tree(path + "\\" + sub)
        winreg.CloseKey(key)
        winreg.DeleteKey(winreg.HKEY_CURRENT_USER, path)
    except OSError:
        try:
            winreg.CloseKey(key)
        except OSError:
            pass


def context_menu_installed():
    if not IS_WINDOWS:
        return False
    try:
        winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                       _KEYS[0] + "\\" + _VERB).Close()
        return True
    except OSError:
        return False


def default_handler_installed():
    if not IS_WINDOWS:
        return False
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, _KEYS[0])
        try:
            val, _ = winreg.QueryValueEx(key, None)
            return val == _VERB
        finally:
            winreg.CloseKey(key)
    except OSError:
        return False


def add_context_menu(exe_path):
    """'Open in Meridian Explorer' on folder, drive, and folder-background
    right-click menus."""
    if not IS_WINDOWS:
        return False, "Windows only."
    try:
        cmd = f'"{exe_path}" "%1"'
        for base in _KEYS:
            _set(base + "\\" + _VERB, "Open in Meridian Explorer")
            _set(base + "\\" + _VERB, f'"{exe_path}"', "Icon")
            _set(base + "\\" + _VERB + r"\command", cmd)
        _set(_BG_KEY + "\\" + _VERB, "Open in Meridian Explorer")
        _set(_BG_KEY + "\\" + _VERB + r"\command", f'"{exe_path}" "%V"')
        return True, None
    except Exception as e:
        return False, str(e)


def remove_context_menu():
    if not IS_WINDOWS:
        return False, "Windows only."
    try:
        # if it was the default handler, clear that first so folders don't
        # point at a verb that no longer exists
        restore_default_handler()
        for base in _KEYS:
            _delete_tree("%s\\%s" % (base, _VERB))
        _delete_tree("%s\\%s" % (_BG_KEY, _VERB))
        return True, None
    except Exception as e:
        return False, str(e)


def set_default_handler(exe_path):
    """Make Meridian Explorer the default folder/drive verb — desktop
    double-clicks and ShellExecute'd folder paths open it instead of
    Windows Explorer. (Navigation inside an already-open Windows Explorer
    window never goes through the shell verb and is unaffected.)"""
    if not IS_WINDOWS:
        return False, "Windows only."
    ok, err = add_context_menu(exe_path)  # the verb must exist to be default
    if not ok:
        return ok, err
    try:
        for base in _KEYS:
            _set(base, _VERB)  # shell key default value = default verb
        return True, None
    except Exception as e:
        return False, str(e)


def restore_default_handler():
    """Clear the default-verb override; Windows Explorer handles folders
    again. Context-menu entries are left in place."""
    if not IS_WINDOWS:
        return False, "Windows only."
    try:
        for base in _KEYS:
            try:
                key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, base, 0,
                                     winreg.KEY_READ | winreg.KEY_WRITE)
                try:
                    winreg.DeleteValue(key, None)
                except OSError:
                    pass  # no default value set — already restored
                finally:
                    winreg.CloseKey(key)
            except OSError:
                pass
        return True, None
    except Exception as e:
        return False, str(e)


# --------------------------------------------------------------------------
# Meridian FileBrowse's default-shell-browser routing — a distinct verb
# from Meridian Explorer's above, so the two toggles don't clash. Points at
# the trampoline exe (filebrowse_shell_handler.py, built as "Meridian
# FileBrowse Shell Handler.exe"), not at Meridian FileBrowse itself, since
# opening a folder should route through Meridian Launcher's Explorer
# section rather than pop a standalone window.
# --------------------------------------------------------------------------

_FILEBROWSE_VERB = "MeridianFileBrowse"


def filebrowse_default_handler_installed():
    if not IS_WINDOWS:
        return False
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, _KEYS[0])
        try:
            val, _ = winreg.QueryValueEx(key, None)
            return val == _FILEBROWSE_VERB
        finally:
            winreg.CloseKey(key)
    except OSError:
        return False


def set_filebrowse_default_handler(trampoline_exe_path):
    """Make folder opens route through the FileBrowse trampoline exe
    instead of Windows Explorer or Meridian Explorer."""
    if not IS_WINDOWS:
        return False, "Windows only."
    try:
        cmd = f'"{trampoline_exe_path}" "%1"'
        for base in _KEYS:
            _set(base + "\\" + _FILEBROWSE_VERB, "Open in Meridian FileBrowse")
            _set(base + "\\" + _FILEBROWSE_VERB + r"\command", cmd)
            _set(base, _FILEBROWSE_VERB)  # shell key default value = default verb
        return True, None
    except Exception as e:
        return False, str(e)


def restore_filebrowse_default_handler():
    """Remove the FileBrowse verb entirely and clear the default-verb
    override, restoring Windows Explorer."""
    if not IS_WINDOWS:
        return False, "Windows only."
    try:
        ok, err = restore_default_handler()
        if not ok:
            return ok, err
        for base in _KEYS:
            _delete_tree(base + "\\" + _FILEBROWSE_VERB)
        return True, None
    except Exception as e:
        return False, str(e)
