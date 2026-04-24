# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path


block_cipher = None
project_dir = Path.cwd()

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
