#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
set -euo pipefail

cd "$(dirname "$0")"

APP_VERSION="$(tr -d '[:space:]' < VERSION)"
FFMPEG_PATH="$(which ffmpeg || true)"
FFPROBE_PATH="$(which ffprobe || true)"

if [ -z "$FFMPEG_PATH" ]; then
  echo "ffmpeg not found on PATH."
  exit 1
fi

if [ -z "$FFPROBE_PATH" ]; then
  echo "ffprobe not found on PATH."
  exit 1
fi

FFMPEG_VERSION="$("$FFMPEG_PATH" -version)"
if echo "$FFMPEG_VERSION" | grep -q -- "--enable-nonfree"; then
  echo "The ffmpeg on PATH was built with --enable-nonfree."
  echo "Do not use nonfree FFmpeg builds for PrepCut releases."
  exit 1
fi

if echo "$FFMPEG_VERSION" | grep -q -- "--enable-gpl"; then
  echo "Using a GPL-enabled FFmpeg build."
  echo "PrepCut is GPL-licensed; publish corresponding source and FFmpeg build info with releases."
fi

mkdir -p vendor/ffmpeg
rm -f vendor/ffmpeg/ffmpeg vendor/ffmpeg/ffprobe
cp "$FFMPEG_PATH" vendor/ffmpeg/ffmpeg
cp "$FFPROBE_PATH" vendor/ffmpeg/ffprobe
chmod +x vendor/ffmpeg/ffmpeg vendor/ffmpeg/ffprobe

if [ ! -d ".venv" ]; then
  python3 -m venv .venv
fi

. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

if [ ! -x "./vendor/ffmpeg/ffmpeg" ]; then
  echo "Missing ./vendor/ffmpeg/ffmpeg"
  echo "Place an executable ffmpeg binary there before packaging."
  exit 1
fi

if [ ! -x "./vendor/ffmpeg/ffprobe" ]; then
  echo "Missing ./vendor/ffmpeg/ffprobe"
  echo "Place an executable ffprobe binary there before packaging."
  exit 1
fi

python -m PyInstaller --clean --noconfirm prepcut.spec
rm -rf dist/PrepCut

DMG_ROOT="$(mktemp -d)"
trap 'rm -rf "$DMG_ROOT"' EXIT

cp -R dist/PrepCut.app "$DMG_ROOT/"
cp README.md "$DMG_ROOT/"
cp VERSION "$DMG_ROOT/"
cp LICENSE "$DMG_ROOT/"
cp THIRD_PARTY_LICENSES.md "$DMG_ROOT/"
cp -R LICENSES "$DMG_ROOT/"

rm -f dist/PrepCut.dmg
hdiutil create \
  -volname "PrepCut ${APP_VERSION}" \
  -srcfolder "$DMG_ROOT" \
  -ov \
  -format UDZO \
  dist/PrepCut.dmg

echo "Built dist/PrepCut.dmg for PrepCut v${APP_VERSION}"
