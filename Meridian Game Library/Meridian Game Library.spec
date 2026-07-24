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


a = Analysis(
    [os.path.join(THIS_DIR, 'main.py')],
    pathex=[],
    binaries=[],
    datas=[],
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
