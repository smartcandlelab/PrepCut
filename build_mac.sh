#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

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

echo "Built dist/PrepCut.app"
