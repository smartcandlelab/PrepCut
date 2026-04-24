# PrepCut

PrepCut is a minimal macOS desktop app for preparing video files for Final Cut Pro and Logic. It uses ffprobe to inspect each file, then uses ffmpeg to remux compatible files or convert only the streams required by the selected settings.

PrepCut always outputs `.mov` files. By default, outputs are written to:

```text
~/Movies/PrepCut
```

## Requirements

- macOS on Apple Silicon
- Python 3.11 or newer for source runs

## What It Does

- Drag video files into the window.
- PrepCut processes files one at a time.
- Supported video is copied without re-encoding.
- Supported audio is copied without re-encoding.
- Incompatible audio can be converted to AAC or PCM 16-bit.
- Unsupported video can fail, convert to ProRes LT, or convert to ProRes 422.
- Emergency Mode forces ProRes 422 video and PCM 16-bit audio.

Output filenames use this format:

```text
original_name - PrepCut.mov
```

If the output already exists, PrepCut appends `_1`, `_2`, and so on.

## Run From Source

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python main.py
```

## FFmpeg For Development

FFmpeg and ffprobe are not included in this repository.

For local development, install FFmpeg with Homebrew:

```bash
brew install ffmpeg
```

PrepCut looks for `ffmpeg` and `ffprobe` in this order:

1. Inside a packaged PrepCut app bundle.
2. `./vendor/ffmpeg/` next to the source code.
3. The system `PATH`.

If PrepCut cannot find them, place executable binaries here:

```text
./vendor/ffmpeg/ffmpeg
./vendor/ffmpeg/ffprobe
```

The repository keeps `vendor/ffmpeg/.gitkeep`, but does not include actual binaries.

## Usage

1. Open PrepCut.
2. Drop video files into the window.
3. Files are written to `~/Movies/PrepCut` unless you change the output folder.
4. Use Settings to choose audio conversion and unsupported video behavior.
5. Enable Emergency Mode only when you want full ProRes 422 + PCM conversion.

Emergency Mode increases file size because it re-encodes both video and audio.

## Settings

Audio conversion for incompatible audio:

- AAC, using the source bitrate when available and above 192k.
- Lossless PCM 16-bit.

Unsupported video handling:

- Fail.
- Convert to ProRes LT.
- Convert to ProRes 422.

Emergency Mode:

- Converts any input to ProRes 422 video and PCM 16-bit audio.
- Overrides all other processing logic.

Settings persist across launches.

## Packaging

Do not commit FFmpeg or ffprobe binaries to this repository.

To prepare a release build, place executable binaries at:

```text
./vendor/ffmpeg/ffmpeg
./vendor/ffmpeg/ffprobe
```

Then run:

```bash
./build_mac.sh
```

The script uses PyInstaller and outputs:

```text
dist/PrepCut.app
```

Release builds may bundle LGPL-compatible FFmpeg and ffprobe binaries. Verify the license of the exact binaries before release.

## DMG Notes

After building `dist/PrepCut.app`, create a DMG containing:

- `PrepCut.app`
- `README.md`

## Troubleshooting

If video codec is unsupported, enable a ProRes fallback in Settings or convert the file with HandBrake.

If ffmpeg is missing, place `ffmpeg` and `ffprobe` in `./vendor/ffmpeg/` or install FFmpeg so both tools are available on `PATH`.
