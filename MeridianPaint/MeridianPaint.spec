# -*- mode: python ; coding: utf-8 -*-
# Build with:  pyinstaller MeridianPaint.spec
#
# Output: dist/MeridianPaint.exe - copy it next to Meridian Launcher's
# own exe (same convention as every other companion exe in this suite).

block_cipher = None

a = Analysis(
    ['meridian_paint.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=['pygame', 'gameinput_api', 'psutil'],
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
    name='MeridianPaint',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    onefile=True,
)
