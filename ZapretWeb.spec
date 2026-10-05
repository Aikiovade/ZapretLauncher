# -*- mode: python ; coding: utf-8 -*-

a = Analysis(
    ['webapp.py'],
    pathex=[],
    binaries=[],
    datas=[('zapret_data.zip', '.'), ('icon.ico', '.'), ('sounds', 'sounds'), ('webui', 'webui')],
    hiddenimports=['webview.platforms.edgechromium', 'webview.platforms.winforms', 'clr_loader', 'pythonnet', 'pypresence'],
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
    name='ZapretWeb',
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
