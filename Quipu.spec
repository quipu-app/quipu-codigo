# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_data_files

datas = [('quipu/assets', 'assets'), ('quipu/web', 'web'), ('quipu/firebase.json', '.'), ('quipu/sincronizacion/credenciales_google.json', 'sincronizacion')]
datas += collect_data_files('googleapiclient')


a = Analysis(
    ['quipu/main.py'],
    pathex=['quipu'],
    binaries=[],
    datas=datas,
    hiddenimports=['sincronizacion.google_drive', 'sincronizacion.motor', 'modulos', 'modulos.agenda', 'modulos.ajustes', 'modulos.base', 'modulos.foco', 'modulos.notas', 'modulos.sonidos', 'modulos.tiempo', 'modulos.web'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Quipu',
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
    icon=['quipu/assets/marca/q.ico'],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Quipu',
)
