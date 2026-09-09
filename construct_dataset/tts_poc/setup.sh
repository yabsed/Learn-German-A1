#!/usr/bin/env bash
# 가상환경을 만들고 음성 모델을 받는다. 한 번만 실행하면 된다.
set -euo pipefail
cd "$(dirname "$0")"

PYTHON="${PYTHON:-python3}"
VENV=".venv"
ROOT="$(cd .. && pwd)"

[ -d "$VENV" ] || "$PYTHON" -m venv "$VENV"
"$VENV/bin/pip" install --quiet --upgrade pip
"$VENV/bin/pip" install --quiet -r "$ROOT/requirements-audio.txt"
"$VENV/bin/python" "$ROOT/tools/say.py" --download-only

command -v ffmpeg >/dev/null || echo "경고: ffmpeg이 없다. mp3 대신 wav로 저장된다."

cat <<'MSG'

준비 완료.

  .venv/bin/python ../tools/say.py Vater "das Mädchen"
  .venv/bin/python ../tools/say.py --file sample_words.txt --alignments
MSG
