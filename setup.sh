#!/usr/bin/env bash
# Installs everything make_video.py needs. Safe to run repeatedly.
set -e
command -v ffmpeg >/dev/null || (apt-get update -qq && apt-get install -y -qq ffmpeg)
pip install --break-system-packages -q -r "$(dirname "$0")/requirements.txt" 2>&1 | grep -v -i warning || true
python3 -c "import piper, faster_whisper; print('setup ok')"
