# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['quipu/main.py'],
    pathex=['quipu'],
    binaries=[],
    datas=[('quipu/assets', 'assets'), ('quipu/web', 'web'), ('quipu/firebase.json', '.')],
    hiddenimports=['modulos', 'modulos.agenda', 'modulos.ajustes', 'modulos.base', 'modulos.foco', 'modulos.notas', 'modulos.sonidos', 'modulos.tiempo', 'modulos.web'],
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
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['quipu/assets/marca/q.ico'],
    version='info_version.txt',
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='Quipu',
)