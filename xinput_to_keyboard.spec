# -*- mode: python ; coding: utf-8 -*-
# Build with:  pyinstaller xinput_to_keyboard.spec
#
# Why this needs to be its own compiled exe (not just run via
# `sys.executable xinput_to_keyboard.py` like a dev/source setup can
# do): in a compiled Meridian Launcher, sys.executable is Meridian
# Launcher's OWN frozen exe, not a real Python interpreter - there's no
# bundled standalone python.exe to hand a .py script to. Running
# "MeridianLauncher.exe xinput_to_keyboard.py" doesn't execute that
# script as Python at all, it just relaunches the compiled app with a
# file path as an ignored argument - which would make the Controller
# Bridge feature silently do nothing in any real compiled install, the
# normal way this whole suite is actually distributed. main.py's
# _controller_bridge_command() prefers this compiled exe over the
# script fallback whenever it's present next to it; the fallback only
# actually works for a from-source run.
#
# Output: dist/XInputToKeyboard.exe - copy it next to Meridian
# Launcher's own exe (same distribution convention as SDL3.dll).
# main.py looks for it right next to itself.

block_cipher = None

a = Analysis(
    ['xinput_to_keyboard.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=['gameinput_api', 'keyboard'],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='XInputToKeyboard',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    onefile=True,
)
