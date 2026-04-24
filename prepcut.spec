# -*- mode: python ; coding: utf-8 -*-
# SPDX-License-Identifier: GPL-3.0-or-later

from pathlib import Path


block_cipher = None
project_dir = Path.cwd()
app_version = (project_dir / "VERSION").read_text(encoding="utf-8").strip()

a = Analysis(
    ["main.py"],
    pathex=[str(project_dir)],
    binaries=[],
    datas=[
        ("vendor/ffmpeg/ffmpeg", "vendor/ffmpeg"),
        ("vendor/ffmpeg/ffprobe", "vendor/ffmpeg"),
    ],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="PrepCut",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="PrepCut",
)
app = BUNDLE(
    coll,
    name="PrepCut.app",
    icon=None,
    bundle_identifier="com.prepcut.app",
    info_plist={
        "CFBundleName": "PrepCut",
        "CFBundleDisplayName": "PrepCut",
        "CFBundleShortVersionString": app_version,
        "CFBundleVersion": app_version,
        "NSHighResolutionCapable": True,
        "CFBundleDocumentTypes": [
            {
                "CFBundleTypeName": "Video Files",
                "CFBundleTypeRole": "Viewer",
                "LSHandlerRank": "Alternate",
                "CFBundleTypeExtensions": [
                    "mov",
                    "mp4",
                    "m4v",
                    "mkv",
                    "webm",
                    "avi",
                ],
            }
        ],
    },
)
