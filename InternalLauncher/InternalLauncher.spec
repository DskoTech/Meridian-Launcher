# -*- mode: python ; coding: utf-8 -*-
# Build with:  pyinstaller InternalLauncher.spec
#
# Output: dist/InternalLauncher.exe - copy it next to Meridian
# Launcher's own exe (same convention as every other companion exe in
# this suite - CyberDeckBrowser.exe, etc.). Plugins/InternalLauncher/
# plugin.json's "exe" field points at "InternalLauncher.exe", resolved
# relative to BASE_DIR (where MeridianLauncher.exe itself lives) by
# plugin_manager.get_plugin_exe_path, not relative to this plugin's own
# folder.

block_cipher = None

a = Analysis(
    ['internal_launcher.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=['psutil'],
    hookspath=[],
    runtime_hooks=[],
    excludes=['gameinput_native'],
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
    name='InternalLauncher',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    onefile=True,
)
