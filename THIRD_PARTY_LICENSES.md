# Third-Party Licenses

PrepCut is licensed under the GNU General Public License version 3 or later.

PrepCut calls FFmpeg and ffprobe for media inspection and processing.

FFmpeg is available from https://ffmpeg.org/.

Release builds may bundle FFmpeg and ffprobe. PrepCut's build script refuses FFmpeg binaries that report `--enable-nonfree`.

GPL-enabled FFmpeg builds are allowed because PrepCut itself is GPL-licensed. The recommended release build is documented in `LICENSES/FFMPEG_BUILD.md`.

PrepCut uses PyQt6 for its desktop UI. PyQt6 is licensed separately by Riverbank Computing.

Before any release, the maintainer must verify the license terms of the exact binaries and Python packages being bundled.

This note is not legal advice.
