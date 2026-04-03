# -*- mode: python ; coding: utf-8 -*-
"""
LunaLite PyInstaller spec file — reproducible builds.
Usage: pyinstaller LunaLite.spec
"""

import os

block_cipher = None

a = Analysis(
    ["src/main.py"],
    pathex=[],
    binaries=[],
    datas=[
        ("locales", "locales"),
        ("assets", "assets"),
    ],
    hiddenimports=[
        "PyQt6.QtCore",
        "PyQt6.QtWidgets",
        "PyQt6.QtGui",
        "PyQt6.sip",
        "google.generativeai",
        "google.auth",
        "google.auth.transport.requests",
        "pyaudiowpatch",
        "numpy",
        "scipy",
        "sqlite3",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "tkinter",
        "_tkinter",
        "unittest",
        "test",
        "tests",
        "xmlrpc",
        "pydoc",
        "doctest",
        "lib2to3",
        "distutils",
        "setuptools",
        "ensurepip",
        "pip",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="LunaLite",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    windowed=True,
    icon="assets/icon.ico",
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="LunaLite",
)
