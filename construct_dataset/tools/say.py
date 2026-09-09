#!/usr/bin/env python3
"""임의의 독일어를 즉석에서 합성한다. 출력 이름은 이 도구의 out/에서만 쓴다."""
from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from piper_tts import DEFAULT_VOICE, ensure_voice, prepare_voice, synthesize, to_mp3, write_wav  # noqa: E402

TRANSLITERATE = str.maketrans(
    {"ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss", "Ä": "ae", "Ö": "oe", "Ü": "ue"}
)


def slugify(text: str) -> str:
    """CLI의 임시 출력에만 쓰는 이름. 데이터셋 오디오에는 쓰지 않는다."""
    value = text.translate(TRANSLITERATE).lower()
    return re.sub(r"[^a-z0-9]+", "_", value).strip("_") or "word"


def read_word_file(path: Path) -> list[str]:
    return [
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.startswith("#")
    ]


def build_args() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="임의의 독일어를 로컬 Piper로 합성한다.")
    parser.add_argument("words", nargs="*", help="합성할 단어나 문장")
    parser.add_argument("-f", "--file", type=Path, help="한 줄에 하나인 텍스트 파일")
    parser.add_argument("-o", "--out", type=Path, default=ROOT / "tts_poc" / "out")
    parser.add_argument("--voice", default=DEFAULT_VOICE)
    parser.add_argument("--voices-dir", type=Path, default=ROOT / "tts_poc" / "voices")
    parser.add_argument("--slow", type=float, default=1.45)
    parser.add_argument("--gap", type=float, default=0.5)
    parser.add_argument("--once", action="store_true", help="느린 재생 없이 한 번만 읽는다")
    parser.add_argument("--format", choices=["mp3", "wav"], default="mp3")
    parser.add_argument("--bitrate", default="64k")
    parser.add_argument("--alignments", action="store_true")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--download-only", action="store_true")
    return parser


def main() -> int:
    args = build_args().parse_args()
    if args.format == "mp3" and not shutil.which("ffmpeg"):
        print("ffmpeg이 없어 wav로 저장한다. mp3를 원하면 ffmpeg을 설치할 것.", file=sys.stderr)
        args.format = "wav"

    if args.download_only:
        print(f"준비 완료: {ensure_voice(args.voices_dir, args.voice)}")
        return 0

    words = list(args.words)
    if args.file:
        words.extend(read_word_file(args.file))
    if not words:
        print("텍스트가 없다. 인자로 주거나 --file로 넘길 것.", file=sys.stderr)
        return 2

    started = time.perf_counter()
    voice = prepare_voice(args.voices_dir, args.voice, include_alignments=args.alignments)
    rate = voice.config.sample_rate
    silence = b"\x00\x00" * int(rate * args.gap)
    args.out.mkdir(parents=True, exist_ok=True)
    print(f"모델 로드 {time.perf_counter() - started:.2f}초, {rate}Hz, 텍스트 {len(words)}개")

    made = skipped = 0
    started = time.perf_counter()
    for word in words:
        slug = slugify(word)
        final = args.out / f"{slug}.{args.format}"
        if final.exists() and not args.force:
            skipped += 1
            continue
        pcm, alignments = synthesize(voice, word, want_alignments=args.alignments)
        if not args.once:
            slow, _ = synthesize(voice, word, args.slow)
            pcm = pcm + silence + slow
        wav = args.out / f"{slug}.wav"
        write_wav(wav, pcm, rate)
        if args.format == "mp3":
            to_mp3(wav, final, args.bitrate)
            wav.unlink()
        if alignments:
            (args.out / f"{slug}.json").write_text(
                json.dumps({"word": word, "alignments": alignments}, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        made += 1
        print(f"  {word:24} -> {final.name}")

    elapsed = time.perf_counter() - started
    per = elapsed / made if made else 0.0
    print(f"\n{made}개 생성, {skipped}개 건너뜀, {elapsed:.2f}초 소요 (항목당 {per:.3f}초)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
