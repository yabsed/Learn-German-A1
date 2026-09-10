"""5단계: 번역된 독일어 예문에 짧은 행간 한국어 주석을 붙인다.

입력  data/wordlist.jsonl   data/sentence_draft.tsv
출력  data/gloss_draft.jsonl

모델은 독일어를 되풀이하지 않는다. 응답의 ``{n, ko}``는 저장할 때
``[n, 뜻]``으로 압축하며, n은 아직 소비하지 않은 독일어 낱말 몇 개를 한
묶음으로 삼는지 나타낸다. 이미 저장된 id는
건너뛰므로 중간에 끊겨도 다음 실행에서 이어진다.

실행  python scripts/05_glosses.py --levels a1 --workers 4
      python scripts/05_glosses.py --levels a1 --limit 60 --dry-run
"""
from __future__ import annotations

import argparse
import json
import re

from pydantic import BaseModel, ConfigDict

from common import (
    GLOSS_DRAFT,
    LEVELS,
    SENTENCE_DRAFT,
    WORDLIST,
    log,
    read_jsonl,
    read_tsv,
    write_jsonl,
)
from ids import unique_sentences
from llm import pick_backend, run_chunks

CHUNK = 20
VERSION = 2
SDK_MODEL = "claude-sonnet-4-5"
TOKEN_RE = re.compile(r"(?:\([A-Za-zÄÖÜäöüß]+\))?[A-Za-zÄÖÜäöüß]+(?:[-/][A-Za-zÄÖÜäöüß]+)*|\d+(?:[.,:]\d+)*")

SYSTEM = """\
너는 A1~B1 독일어 예문에 행간 한국어 주석을 다는 편집자다.
입력은 탭으로 나눈 id, 독일어 원문, 자연스러운 한국어 번역이다.

- 독일어의 모든 문자 낱말과 숫자 토큰을 원래 순서대로 정확히 한 번 소비한다.
- 각 g 항목은 {"n": 연속된 토큰 수, "ko": 그 범위의 문맥상 한국어 뜻}이다.
- 기본은 반드시 한 토큰당 한 항목(n=1)이다. 관사·대명사·조동사·전치사에도 짧은 기능 뜻을 단다.
- 따로 풀이하면 명백히 잘못되는 고정 숙어와 문법 표현만 2~3토큰으로 묶는다.
- 주어+동사, 관사+명사, 수식어+명사, 평범한 절을 편의를 위해 묶지 않는다. n은 3을 넘지 않는다.
- 뜻은 사전식으로 짧게 쓴다. 대응 뜻이 없는 기능어는 '(관사)'처럼 기능을 쓴다.
- 문장 종결, 해설, 괄호 속 대안은 쓰지 않는다.
- 조사와 어미는 이해에 필요할 때 붙인다. 자연 번역과 의미가 충돌해서는 안 된다.
- 독일어 원문과 전체 한국어 번역을 출력에 되풀이하지 않는다.
- 출력은 스키마에 맞는 JSON만 쓰고 id를 빼거나 더하지 않는다."""


class GlossPair(BaseModel):
    """모델 전송용 객체. 저장할 때는 반복 키를 버리고 [n, ko]로 압축한다."""
    model_config = ConfigDict(extra="forbid")

    n: int
    ko: str


class GlossItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    g: list[GlossPair]


class GlossBatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[GlossItem]


# 테스트의 동적 import에서도 지연된 타입 이름을 같은 방식으로 해석한다.
GlossItem.model_rebuild(_types_namespace={"GlossPair": GlossPair})
GlossBatch.model_rebuild(_types_namespace={"GlossItem": GlossItem, "GlossPair": GlossPair})


def word_count(text: str) -> int:
    return len(TOKEN_RE.findall(text))


def valid_gloss(item: GlossItem, sentence: dict) -> bool:
    """형식 오류는 모델에게 설명시키지 않고 값싼 로컬 검사로 거른다."""
    return (
        bool(item.g)
        and all(pair.n > 0 and pair.ko.strip() and len(pair.ko.strip()) <= 30 for pair in item.g)
        and sum(pair.n for pair in item.g) == word_count(sentence["de"])
    )


def build_prompt(entries: list[dict]) -> str:
    rows = [
        "\t".join((entry["id"], entry["de"].replace("\t", " "), entry["ko"].replace("\t", " ")))
        for entry in entries
    ]
    return f"다음 {len(rows)}개 예문의 g를 써라.\n" + "\n".join(rows)


def read_drafts() -> list[dict]:
    if not GLOSS_DRAFT.exists():
        return []
    rows = read_jsonl(GLOSS_DRAFT)
    unique = []
    seen = set()
    for row in rows:
        key = (row.get("id"), row.get("v"))
        if key not in seen:
            unique.append(row)
            seen.add(key)
    if len(unique) != len(rows):
        write_jsonl(GLOSS_DRAFT, unique)
        log(f"glosses: removed {len(rows) - len(unique)} duplicate draft rows")
    return unique


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--levels", default=",".join(LEVELS))
    ap.add_argument("--backend", choices=["auto", "sdk", "cli", "codex"], default="auto")
    ap.add_argument("--model", default=None)
    ap.add_argument("--effort", choices=["low", "medium", "high", "max"], default="low")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--chunk", type=int, default=CHUNK)
    ap.add_argument("--limit", type=int, default=None, help="처음 N개만 (탐침용)")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    levels = {level.strip().lower() for level in args.levels.split(",") if level.strip()}
    translations = {row["id"]: row["ko"] for row in read_tsv(SENTENCE_DRAFT) if row.get("ko")}
    entries = [
        {**sentence, "ko": translations[sentence["id"]]}
        for sentence in unique_sentences(read_jsonl(WORDLIST))
        if sentence["level"] in levels and sentence["id"] in translations
    ]
    done = {row.get("id") for row in read_drafts() if row.get("v") == VERSION}
    todo = [entry for entry in entries if entry["id"] not in done]
    if args.limit is not None:
        todo = todo[:args.limit]
    chunks = [todo[i:i + args.chunk] for i in range(0, len(todo), args.chunk)]
    log(
        f"glosses: {len(entries)} translated entries in {sorted(levels)}, "
        f"{len(done)} already drafted, {len(todo)} to do in {len(chunks)} chunks"
    )

    if args.dry_run:
        if chunks:
            print(build_prompt(chunks[0]))
        return
    if not chunks:
        return

    backend = pick_backend(args.backend)
    model_label = args.model or (SDK_MODEL if backend == "sdk" else f"{backend}-default")
    log(f"  backend={backend} model={model_label} effort={args.effort} workers={args.workers}")
    by_id = {entry["id"]: entry for entry in todo}
    fh = GLOSS_DRAFT.open("a", encoding="utf-8")

    def save(items: list[GlossItem], used: str) -> None:
        for item in items:
            row = {"id": item.id, "g": [[pair.n, pair.ko.strip()] for pair in item.g], "model": used, "v": VERSION}
            fh.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")
        fh.flush()

    try:
        run_chunks(
            todo,
            label="glosses",
            system=SYSTEM,
            build_prompt=build_prompt,
            batch_type=GlossBatch,
            valid_item=lambda item: item.id in by_id and valid_gloss(item, by_id[item.id]),
            save=save,
            backend=backend,
            model=args.model,
            sdk_model=SDK_MODEL,
            effort=args.effort,
            workers=args.workers,
            chunk_size=args.chunk,
        )
    finally:
        fh.close()
    log(f"glosses: → {GLOSS_DRAFT}")


if __name__ == "__main__":
    main()
