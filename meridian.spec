# -*- mode: python ; coding: utf-8 -*-
# Build with:  pyinstaller meridian.spec
# (or just run compile.bat, which does this for you)
#
# Notes:
# - keyboard_controls.json / controller_controls.json / settings.json /
#   cached thumbnails are generated at first run under
#   %LOCALAPPDATA%\Meridian Launcher\, so they are NOT bundled as read-only
#   datas here — they need to stay writable regardless of where the exe
#   itself is installed (e.g. Program Files).
# - VERSION is bundled read-only (see datas below) and read at runtime via
#   sys._MEIPASS — it's what the update checker (updater.py) compares
#   against the latest GitHub release tag. Bump it before tagging a new
#   release.
# - onscreenmenu launching (for sections/system features with "Launch
#   with onscreenmenu?" enabled, on by default) is fully internalized -
#   no companion osm.bat file needed anymore, see _launch_onscreenmenu().
# - Optional companion executables the app looks for in its own folder:
#   CyberDeckBrowser.exe (Web section), Meridian_Explorer.exe (Files
#   section), Meridian Game Library.exe (Games section's "Game Library"
#   entry).

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[('frontend', 'frontend'), ('VERSION', '.')],
    hiddenimports=[
        'webview.platforms.winforms',
        'webview.platforms.edgechromium',
        'win32gui', 'win32con', 'win32api',
        'psutil',
        # audio_devices.py, phone_type_server.py, and the Controller
        # Bridge keystroke injection all import these inside a
        # try/except ImportError block - PyInstaller's static analyzer
        # doesn't reliably see through that, so without listing them
        # explicitly here they silently never get bundled at all
        # (the app still builds "successfully" with no error, it just
        # doesn't work at runtime, or the .spec build itself fails
        # depending on what else is missing at analysis time).
        'pycaw', 'pycaw.pycaw', 'comtypes', 'comtypes.stream',
        'qrcode', 'keyboard',
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=['gameinput_native'],  # see gameinput_api.py's sys.path fix - this stops
    # PyInstaller's build-time analyzer from baking in a hollow reference to the
    # SOURCE folder (repo root's gameinput_native/, sitting right next to main.py),
    # which otherwise permanently shadows the real, externally-placed .pyd at
    # runtime - see gameinput_native/README.md's "Distributing it" section.
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
