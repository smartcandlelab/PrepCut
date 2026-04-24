# Recommended FFmpeg Release Build

PrepCut release DMGs should bundle FFmpeg and ffprobe binaries built from official FFmpeg source.

Recommended source:

```text
https://ffmpeg.org/releases/ffmpeg-7.1.1.tar.xz
```

Recommended configure line:

```bash
./configure \
  --prefix="$PREFIX" \
  --disable-gpl \
  --disable-nonfree \
  --disable-doc \
  --disable-debug \
  --disable-ffplay \
  --disable-sdl2 \
  --disable-network \
  --disable-autodetect \
  --disable-lzma \
  --disable-iconv \
  --enable-pthreads \
  --enable-videotoolbox \
  --enable-audiotoolbox \
  --enable-zlib \
  --enable-bzlib \
  --cc=clang
```

This build provides the codecs PrepCut needs while avoiding unnecessary external codec libraries.

GPL-enabled FFmpeg builds may also be used because PrepCut is GPL-licensed. Do not use FFmpeg builds configured with `--enable-nonfree` for public releases.

For each published DMG, keep the exact FFmpeg source, configure line, and any local patches available with the release.
