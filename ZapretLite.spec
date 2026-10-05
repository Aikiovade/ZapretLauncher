# -*- mode: python ; coding: utf-8 -*-
# D7: lite-сборка без встроенного zapret_data.zip (payload скачивается при первом старте
# через update_zapret_data()/ensure_payload; интернет нужен только для первой загрузки пакета).

a = Analysis(
    ['webapp.py'],
    pathex=[],
    binaries=[],
    datas=[('icon.ico', '.'), ('sounds', 'sounds'), ('webui', 'webui')],
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
    name='ZapretLite',
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
