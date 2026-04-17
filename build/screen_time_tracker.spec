# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec file for Screen Time Tracker"""

import sys
import os

block_cipher = None

# Get the project root directory
project_root = os.path.dirname(os.path.dirname(os.path.abspath(SPEC)))

a = Analysis(
    [os.path.join(project_root, 'src', 'main.py')],
    pathex=[project_root],
    binaries=[],
    datas=[],
    hiddenimports=[
        # pywin32 hidden imports
        'win32timezone',
        'win32api',
        'win32con',
        'win32event',
        'win32gui',
        'win32process',
        'winerror',
        # pystray
        'pystray._win32',
        # PIL
        'PIL._tkinter_finder',
        # tkinter
        'tkinter',
        'tkinter.filedialog',
        'tkinter.messagebox',
        'tkinter.ttk',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter.test',
        'unittest',
        'pydoc',
        'doctest',
        'difflib',
        'pdb',
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
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='ScreenTimeTracker',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # No console window for GUI app
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # Version info will show in file properties
    version=None,
    icon=None,  # Icon is generated dynamically
    uac_admin=False,  # Does not require admin
    onefile=True,  # Single executable file
)
