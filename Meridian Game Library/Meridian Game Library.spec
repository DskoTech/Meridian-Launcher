# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_submodules
import os

# SPECPATH is a builtin PyInstaller injects into every .spec file's exec
# namespace - the directory containing THIS .spec file, regardless of
# where the repo actually lives on disk or what the current working
# directory is when `pyinstaller` gets invoked. The two absolute
# C:\Users\Administrator\... paths this file used to hardcode only ever
# worked on the exact machine they were generated on - anyone else's
# build failed immediately since that path simply doesn't exist for them.
THIS_DIR = os.path.abspath(SPECPATH)

hiddenimports = ['win32timezone']
hiddenimports += collect_submodules('webview')
# system_actions.py imports these inside try/except ImportError blocks -
# PyInstaller's static analyzer doesn't reliably see through that, so
# without listing them explicitly here they silently never get bundled
# at all (the app still builds "successfully", it just quietly loses
# battery status, Wi-Fi/Bluetooth control, and process management at
# runtime instead of erroring anywhere obvious).
hiddenimports += ['psutil', 'win32gui', 'win32con', 'win32api', 'win32process']

# Native Rust backend, if built (BuildMeridianCore.bat stages it here).
# Conditional so a spec build without it still works (pure-Python fallback).
_core_binaries = []
_core_pyd = os.path.join(THIS_DIR, 'meridian_core.pyd')
if os.path.exists(_core_pyd):
    _core_binaries.append((_core_pyd, '.'))
    hiddenimports += ['meridian_core']


a = Analysis(
    [os.path.join(THIS_DIR, 'main.py')],
    pathex=[],
    binaries=_core_binaries,
    datas=_core_binaries + ([
        (os.path.join(THIS_DIR, 'idle_optimizer.py'), '.'),
    ] if os.path.exists(os.path.join(THIS_DIR, 'idle_optimizer.py')) else []),
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['gameinput_native'],  # see gameinput_api.py's sys.path fix / meridian.spec's own excludes comment
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Meridian Game Library',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=[os.path.join(THIS_DIR, 'icon.ico')],
    contents_directory='MeridianGameLibrary_internal',
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Meridian Game Library',
)
