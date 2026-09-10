"""8단계: 앱이 읽을 등급별 묶음과 오디오를 app/ 으로 옮긴다.

words.json·sentences.json 전체는 3 MB 가까이 된다. 앱은 한 번에 한 등급만
쓰므로 등급 하나만 담은 파일을 따로 만든다. 오디오는 복사하지 않고 하드링크로
걸어 같은 파일을 두 번 저장하지 않는다. 같은 파일 시스템이 아니면 복사한다.

실행  python scripts/08_site.py --levels a1
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
from datetime import date
from pathlib import Path

from common import AUDIO, LEVELS, ROOT, SENTENCES, WORDS, log

SITE = ROOT.parent / "app"


def read_json(path: Path):
    if not path.exists():
        raise SystemExit(f"입력 파일이 없다: {path}. 먼저 make merge를 실행할 것.")
    return json.loads(path.read_text(encoding="utf-8"))


def bundle(words: list[dict], sentences: list[dict], level: str) -> dict:
    """등급 하나의 단어와, 그 단어들이 실제로 가리키는 예문만 담는다."""
    by_id = {s["id"]: s for s in sentences}
    picked, used = [], {}
    for word in words:
        if word["level"].lower() != level:
            continue
        example_ids = []
        for example in word.get("examples") or []:
            sentence = by_id.get(example["id"])
            if sentence is None:
                continue
            packed = {"de": sentence["de"], "ko": sentence["ko"], "en": sentence["en"]}
            if sentence.get("g"):
                packed["g"] = sentence["g"]
            used[sentence["id"]] = packed
            example_ids.append(sentence["id"])
        picked.append({
            "id": word["id"],
            "de": word["de"],
            "lemma": word["lemma"],
            "article": word["article"],
            "plural": word["plural"],
            "variants": word.get("variants") or [],
            "ipa": word["ipa"],
            "ko": word["ko"],
            "note": word["note"],
            "pos": word["pos"],
            "ex": example_ids,
        })
    return {
        "level": level.upper(),
        "built": date.today().isoformat(),
        "words": picked,
        "sentences": used,
    }


def link_audio(ids: list[str], out: Path) -> tuple[int, int, int]:
    """있는 mp3를 하드링크한다. (새로 건 것, 이미 있던 것, 원본이 없는 것)"""
    out.mkdir(parents=True, exist_ok=True)
    linked = kept = missing = 0
    for item_id in ids:
        source = AUDIO / f"{item_id}.mp3"
        target = out / f"{item_id}.mp3"
        if not source.exists():
            missing += 1
            continue
        if target.exists():
            # 같은 inode 면 이미 같은 파일이다. 크기로 견주면 다시 만든 mp3 가
            # 우연히 같은 크기일 때 옛 링크가 남는다.
            if target.stat().st_ino == source.stat().st_ino:
                kept += 1
                continue
            target.unlink()
        try:
            os.link(source, target)
        except OSError:
            shutil.copy2(source, target)
        linked += 1
    return linked, kept, missing


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--levels", default="a1", help="쉼표로 구분. 기본 a1")
    ap.add_argument("--out", type=Path, default=SITE)
    ap.add_argument("--no-audio", action="store_true", help="데이터 파일만 만든다")
    args = ap.parse_args()

    levels = [level.strip().lower() for level in args.levels.split(",") if level.strip()]
    unknown = set(levels) - set(LEVELS)
    if unknown:
        ap.error(f"알 수 없는 등급: {','.join(sorted(unknown))}")

    words, sentences = read_json(WORDS), read_json(SENTENCES)
    built = []
    for level in levels:
        data = bundle(words, sentences, level)
        if not data["words"]:
            log(f"site: {level} 단어가 없다. 건너뛴다.")
            continue
        path = args.out / "data" / f"{level}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        size = path.stat().st_size / 1024
        log(f"site: {path.relative_to(args.out)} — 단어 {len(data['words'])}, 예문 {len(data['sentences'])}, {size:.0f} KB")
        built.append(data)

        if not args.no_audio:
            ids = [w["id"] for w in data["words"]] + list(data["sentences"])
            linked, kept, missing = link_audio(ids, args.out / "audio")
            log(f"  오디오 {len(ids)}개 중 새로 {linked}, 그대로 {kept}, 원본 없음 {missing}")

    if not built:
        raise SystemExit("만든 것이 없다.")
    manifest = args.out / "data" / "levels.json"
    manifest.write_text(json.dumps(
        [{"level": d["level"], "words": len(d["words"]), "sentences": len(d["sentences"])} for d in built],
        ensure_ascii=False, indent=1), encoding="utf-8")
    log(f"site: {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
