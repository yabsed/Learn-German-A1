#!/usr/bin/env python3
"""임의의 독일어 단어를 이 노트북에서 mp3로 합성한다.

한 단어당 오디오 하나를 만들고, 그 안에서 같은 단어를 두 번 읽는다.
첫 번째는 보통 속도, 0.5초 쉰 뒤 두 번째는 느린 속도다. 초보자가
움라우트나 ch처럼 한국어에 없는 소리를 두 번째 재생에서 분리해
들으라는 뜻이다.

네트워크는 음성 모델을 처음 받을 때만 쓴다. 그 뒤로는 전부 오프라인,
CPU만으로 돈다.

    python synth.py Vater "das Mädchen"
    python synth.py --file sample_words.txt --alignments
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import time
import wave
from pathlib import Path

from piper import PiperVoice, SynthesisConfig
from piper.download_voices import download_voice

HERE = Path(__file__).resolve().parent
DEFAULT_VOICE = "de_DE-thorsten-high"

# 파일명을 ASCII로 유지한다. 웹 서버와 압축 도구가 움라우트를 다루는 방식이
# 제각각이라, 파일명에서는 아예 없애는 편이 사고가 적다.
TRANSLITERATE = str.maketrans(
    {"ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss", "Ä": "ae", "Ö": "oe", "Ü": "ue"}
)


def slugify(word: str) -> str:
    """'das Mädchen' -> 'das_maedchen'."""
    s = word.translate(TRANSLITERATE).lower()
    s = re.sub(r"[^a-z0-9]+", "_", s).strip("_")
    return s or "word"


def read_word_file(path: Path) -> list[str]:
    words = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            words.append(line)
    return words


def ensure_voice(voices_dir: Path, name: str) -> Path:
    """음성 모델이 없으면 받는다. 있으면 그대로 쓴다."""
    onnx = voices_dir / f"{name}.onnx"
    if not onnx.exists():
        voices_dir.mkdir(parents=True, exist_ok=True)
        print(f"음성 모델 내려받는 중: {name}", file=sys.stderr)
        download_voice(name, voices_dir)
    return onnx


def synthesize(voice: PiperVoice, text: str, length_scale: float, want_alignments: bool):
    """단어 하나를 한 속도로 읽어 16비트 PCM 바이트열과 음소 정렬을 돌려준다."""
    cfg = SynthesisConfig(length_scale=length_scale)
    chunks = list(voice.synthesize(text, syn_config=cfg,
                                   include_alignments=want_alignments))
    pcm = b"".join(c.audio_int16_bytes for c in chunks)

    alignments = None
    if want_alignments:
        alignments, cursor = [], 0.0
        rate = voice.config.sample_rate
        for chunk in chunks:
            for a in (chunk.phoneme_alignments or []):
                seconds = a.num_samples / rate
                alignments.append(
                    {"phoneme": a.phoneme,
                     "start": round(cursor, 4),
                     "duration": round(seconds, 4)}
                )
                cursor += seconds
    return pcm, alignments


def write_wav(path: Path, pcm: bytes, sample_rate: int) -> None:
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sample_rate)
        w.writeframes(pcm)


def to_mp3(wav_path: Path, mp3_path: Path, bitrate: str) -> None:
    subprocess.run(
        ["ffmpeg", "-loglevel", "error", "-y", "-i", str(wav_path),
         "-codec:a", "libmp3lame", "-b:a", bitrate, "-ac", "1", str(mp3_path)],
        check=True,
    )


def build_args() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="독일어 단어를 로컬에서 두 속도 오디오로 합성한다.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("words", nargs="*", help="합성할 단어. 관사를 붙여도 된다.")
    p.add_argument("-f", "--file", type=Path, help="한 줄에 한 단어인 텍스트 파일")
    p.add_argument("-o", "--out", type=Path, default=HERE / "out", help="출력 디렉토리")
    p.add_argument("--voice", default=DEFAULT_VOICE, help=f"음성 모델 (기본 {DEFAULT_VOICE})")
    p.add_argument("--voices-dir", type=Path, default=HERE / "voices",
                   help="음성 모델을 보관할 디렉토리")
    p.add_argument("--slow", type=float, default=1.45,
                   help="느린 재생의 배속 계수. 클수록 느리다 (기본 1.45)")
    p.add_argument("--gap", type=float, default=0.5, help="두 재생 사이 무음 초 (기본 0.5)")
    p.add_argument("--once", action="store_true", help="느린 재생 없이 한 번만 읽는다")
    p.add_argument("--format", choices=["mp3", "wav"], default="mp3")
    p.add_argument("--bitrate", default="64k", help="mp3 비트레이트 (기본 64k)")
    p.add_argument("--alignments", action="store_true",
                   help="음소별 타임스탬프를 같은 이름의 .json으로 저장")
    p.add_argument("--force", action="store_true", help="이미 있는 파일도 다시 만든다")
    p.add_argument("--download-only", action="store_true",
                   help="음성 모델만 받고 끝낸다. 설치 확인용")
    return p


def main() -> int:
    args = build_args().parse_args()

    if args.format == "mp3" and not shutil.which("ffmpeg"):
        print("ffmpeg이 없어 wav로 저장한다. mp3를 원하면 ffmpeg을 설치할 것.",
              file=sys.stderr)
        args.format = "wav"

    onnx = ensure_voice(args.voices_dir, args.voice)
    if args.download_only:
        print(f"준비 완료: {onnx}")
        return 0

    words = list(args.words)
    if args.file:
        words += read_word_file(args.file)
    if not words:
        print("단어가 없다. 인자로 주거나 --file로 넘길 것.", file=sys.stderr)
        return 2

    started = time.perf_counter()
    voice = PiperVoice.load(onnx, include_alignments=args.alignments)
    rate = voice.config.sample_rate
    silence = b"\x00\x00" * int(rate * args.gap)
    args.out.mkdir(parents=True, exist_ok=True)
    print(f"모델 로드 {time.perf_counter() - started:.2f}초, {rate}Hz, 단어 {len(words)}개")

    made = skipped = 0
    started = time.perf_counter()
    for word in words:
        slug = slugify(word)
        final = args.out / f"{slug}.{args.format}"
        if final.exists() and not args.force:
            skipped += 1
            continue

        pcm, alignments = synthesize(voice, word, 1.0, args.alignments)
        if not args.once:
            slow, _ = synthesize(voice, word, args.slow, False)
            pcm = pcm + silence + slow

        wav = args.out / f"{slug}.wav"
        write_wav(wav, pcm, rate)
        if args.format == "mp3":
            to_mp3(wav, final, args.bitrate)
            wav.unlink()

        if alignments:
            (args.out / f"{slug}.json").write_text(
                json.dumps({"word": word, "alignments": alignments},
                           ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        made += 1
        print(f"  {word:24} -> {final.name}")

    elapsed = time.perf_counter() - started
    per = elapsed / made if made else 0.0
    print(f"\n{made}개 생성, {skipped}개 건너뜀, {elapsed:.2f}초 소요 "
          f"(단어당 {per:.3f}초)")
    if per:
        print(f"1300단어 환산 약 {per * 1300 / 60:.1f}분")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
