# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['zapret_new_win.py'],
    pathex=[],
    binaries=[],
    datas=[('zapret_data.zip', '.'), ('icon.ico', '.'), ('sounds', 'sounds')],
    hiddenimports=['pypresence'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['numpy', 'numpy.libs', 'yaml', 'PIL.AvifImagePlugin'],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='Zapret',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    uac_admin=True,
    icon=['icon.ico'],
)
