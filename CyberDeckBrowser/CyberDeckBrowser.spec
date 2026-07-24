# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

# osk.bat used to be bundled here too - no longer needed, OSK toggling
# is fully internalized now (see run_osk() in ui/main_window.py), and
# the file itself was moved to obsolete/osk_osm_bat_files/ - referencing
# it here as a datas entry would hard-fail the build since PyInstaller
# requires every datas source file to actually exist.
datas = [('icon.ico', '.')]
binaries = []
hiddenimports = [
    # Imported inside a try/except ImportError block in main.py -
    # PyInstaller's static analyzer doesn't reliably see through that,
    # so without listing it explicitly it silently never gets bundled.
    'psutil',
]
tmp_ret = collect_all('PySide6.QtWidgets')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('PySide6.QtGui')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('PySide6.QtCore')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('PySide6.QtWebEngineWidgets')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('PySide6.QtWebEngineCore')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('PySide6.QtNetwork')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('shiboken6')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]


a = Analysis(
    ['launcher.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['PySide6.QtQml', 'PySide6.QtQuick', 'PySide6.QtQuickWidgets', 'PySide6.QtQuick3D', 'PySide6.QtQuickControls2', 'PySide6.QtMultimedia', 'PySide6.QtMultimediaWidgets', 'PySide6.QtPdf', 'PySide6.QtPdfWidgets', 'PySide6.QtBluetooth', 'PySide6.QtNfc', 'PySide6.QtPositioning', 'PySide6.QtSensors', 'PySide6.QtSerialPort', 'PySide6.QtSql', 'PySide6.QtTest', 'PySide6.QtDesigner', 'PySide6.QtHelp', 'PySide6.Qt3DCore', 'PySide6.Qt3DRender', 'PySide6.QtCharts', 'PySide6.QtDataVisualization', 'PySide6.QtRemoteObjects', 'PySide6.QtScxml', 'PySide6.QtStateMachine', 'PySide6.QtTextToSpeech', 'gameinput_native'],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='CyberDeckBrowser',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['icon.ico'],
    contents_directory='CyberDeckBrowser_internal',
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='CyberDeckBrowser',
)
