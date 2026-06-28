# -*- mode: python ; coding: utf-8 -*-
"""
LDKLauncher.spec — PyInstaller (PySide6, onedir)

Build:
    pyinstaller LDKLauncher.spec --clean
Saída: dist\LDKLauncher\LDKLauncher.exe
"""

a = Analysis(
    ['launcher/main.py'],
    pathex=['.', 'launcher'],   # '.' → encontra shared/; 'launcher/' → imports sem prefixo do main.py
    binaries=[],
    datas=[
        ('launcher/assets', 'assets'),  # → _MEIPASS/assets/ (ldkf.ico, check.svg, notification.wav)
    ],
    hiddenimports=[
        # Google API — PyInstaller não descobre automaticamente via análise estática
        'google.oauth2.service_account',
        'googleapiclient.discovery',
        'googleapiclient.http',
        'googleapiclient._helpers',
        'google.auth.transport.requests',
        'google.auth._default',
        # PySide6 — QtMultimedia é usado para o som da notificação
        'PySide6.QtMultimedia',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='LDKLauncher',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,          # sem janela de console preta
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='launcher/assets/ldkf.ico',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='LDKLauncher',     # → dist\LDKLauncher\
)
