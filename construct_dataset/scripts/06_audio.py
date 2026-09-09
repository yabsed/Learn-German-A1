"""6단계: words.json·sentences.json의 id로 mp3를 만든다.

단어는 lemma를 보통 속도와 느린 속도로 두 번 읽고, 예문은 보통 속도로 한
번 읽는다. 파일명은 텍스트에서 만들지 않고 데이터셋의 id를 그대로 쓴다.

속도가 1.0 이 아닌 이유는 Piper 가 그 값에서 초당 18자로 읽기 때문이다.
같은 문장을 읽은 실제 화자(Thorsten, 이 음성 모델의 원본)는 16.3자였다.

단어와 예문은 일부러 다른 속도를 쓴다. 들어 보고 고른 값이다.
단어는 1.25(초당 15.4자)로 화자와 비슷하게 두었다. 짧아서 더 늦추면
늘어지고, 어차피 2.3 으로 한 번 더 읽어 주므로 첫 읽기까지 느릴 이유가 없다.
예문은 1.6(초당 12.7자)으로 화자보다 느리다. 길어서 따라 읽으려면 그만큼
여유가 필요하다. 이 값도 화자 본인의 발화 범위(초당 10~17자) 안에는 든다.

실행  python scripts/06_audio.py --levels a1
      python scripts/06_audio.py --levels a1,a2 --force
      python scripts/06_audio.py --levels a1 --only sentences --force
"""
from __future__ import annotations

import argparse
import json
import shutil
import time
from pathlib import Path

from common import AUDIO, LEVELS, ROOT, SENTENCES, WORDS, log
from piper_tts import DEFAULT_VOICE, prepare_voice, synthesize, to_mp3, write_wav

DEFAULT_VOICES_DIR = ROOT / "tts_poc" / "voices"


def work_items(words: list[dict], sentences: list[dict], levels: set[str],
               word_scale: float = 1.25, slow: float = 1.8,
               sentence_scale: float = 1.6, only: str = "all"):
    """(데이터셋 id, 읽을 텍스트, 읽을 속도들) 을 만든다.

    속도가 둘이면 그 둘을 무음으로 이어 붙인다. 단어는 보통 속도로 한 번,
    느린 속도로 한 번 더. 예문은 그보다 느린 속도로 한 번만.
    """
    seen: set[str] = set()
    if only in ("all", "words"):
        for word in words:
            if word["level"].lower() in levels:
                item_id = word["id"]
                if item_id in seen:
                    raise ValueError(f"duplicate audio id: {item_id}")
                seen.add(item_id)
                yield item_id, word["lemma"], (word_scale, slow)
    if only in ("all", "sentences"):
        for sentence in sentences:
            if sentence["level"].lower() in levels:
                item_id = sentence["id"]
                if item_id in seen:
                    raise ValueError(f"duplicate audio id: {item_id}")
                seen.add(item_id)
                yield item_id, sentence["de"], (sentence_scale,)


def read_json(path: Path) -> list[dict]:
    if not path.exists():
        raise SystemExit(f"입력 파일이 없다: {path}. 먼저 make merge를 실행할 것.")
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--levels", default=",".join(LEVELS), help="쉼표로 구분. 기본 a1,a2,b1")
    ap.add_argument("--out", type=Path, default=AUDIO)
    ap.add_argument("--voice", default=DEFAULT_VOICE)
    ap.add_argument("--voices-dir", type=Path, default=DEFAULT_VOICES_DIR)
    ap.add_argument("--word-scale", type=float, default=1.25, help="단어 첫 읽기의 길이 계수")
    ap.add_argument("--slow", type=float, default=1.8, help="단어의 느린 읽기 길이 계수")
    ap.add_argument("--sentence-scale", type=float, default=1.6, help="예문의 길이 계수")
    ap.add_argument("--only", choices=("all", "words", "sentences"), default="all",
                    help="일부만 다시 만들 때 쓴다")
    ap.add_argument("--gap", type=float, default=0.5, help="단어의 두 읽기 사이 무음 초")
    ap.add_argument("--bitrate", default="32k")
    ap.add_argument("--limit", type=int, default=None, help="처음 N개만 (시험용)")
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    levels = {level.strip().lower() for level in args.levels.split(",") if level.strip()}
    unknown = levels.difference(LEVELS)
    if unknown:
        ap.error(f"알 수 없는 등급: {','.join(sorted(unknown))}")
    if not shutil.which("ffmpeg"):
        raise SystemExit("ffmpeg이 없다. 데이터셋 오디오는 mp3로 만들어야 하므로 ffmpeg을 설치할 것.")

    items = list(work_items(read_json(WORDS), read_json(SENTENCES), levels,
                            word_scale=args.word_scale, slow=args.slow,
                            sentence_scale=args.sentence_scale, only=args.only))
    if args.limit is not None:
        items = items[:args.limit]
    pending = [item for item in items if args.force or not (args.out / f"{item[0]}.mp3").exists()]
    skipped = len(items) - len(pending)
    log(f"audio: {len(items)} items in {sorted(levels)} ({args.only}), "
        f"word {args.word_scale}/{args.slow}, sentence {args.sentence_scale}, "
        f"{skipped} existing, {len(pending)} to make")
    if not pending:
        return 0

    args.out.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    voice = prepare_voice(args.voices_dir, args.voice)
    rate = voice.config.sample_rate
    silence = b"\x00\x00" * int(rate * args.gap)
    log(f"  model loaded in {time.perf_counter() - started:.2f}s, {rate}Hz")

    started = time.perf_counter()
    for index, (item_id, text, scales) in enumerate(pending, 1):
        pcm = silence.join(synthesize(voice, text, scale)[0] for scale in scales)
        wav = args.out / f".{item_id}.wav"
        encoded = args.out / f".{item_id}.mp3"
        final = args.out / f"{item_id}.mp3"
        try:
            write_wav(wav, pcm, rate)
            to_mp3(wav, encoded, args.bitrate)
            encoded.replace(final)
        finally:
            wav.unlink(missing_ok=True)
            encoded.unlink(missing_ok=True)
        if index % 100 == 0 or index == len(pending):
            log(f"  {index}/{len(pending)} made")

    elapsed = time.perf_counter() - started
    log(f"audio: {len(pending)} made, {skipped} skipped in {elapsed:.1f}s → {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
