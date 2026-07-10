# -*- mode: python ; coding: utf-8 -*-
# Build with:  pyinstaller meridian.spec
# (or just run compile.bat, which does this for you)
#
# Notes:
# - keyboard_controls.json / controller_controls.json / settings.json are
#   generated at first run next to the .exe, so they are NOT bundled as
#   read-only datas here — they need to stay writable in the install folder.
# - Drop osm.bat next to the built Meridian Launcher.exe if you want
#   sections/system features with "Launch with onscreenmenu?" enabled
#   (on by default) to trigger it; the app looks for it in its own directory.
# - Optional companion executables the app looks for in its own folder:
#   CyberDeckBrowser.exe (Web section), Meridian_Explorer.exe (Files
#   section), Meridian Game Library.exe (Games section's "Game Library"
#   entry).

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[('frontend', 'frontend')],
    hiddenimports=[
        'webview.platforms.winforms',
        'webview.platforms.edgechromium',
        'win32gui', 'win32con', 'win32api',
        'psutil',
    ],
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
    name='MeridianLauncher',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    onefile=True,
    icon='icon.ico',
)
