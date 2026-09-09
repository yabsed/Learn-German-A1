"""4단계: 독일어 예문에 한국어 번역 초안을 붙인다.

입력  data/wordlist.jsonl
출력  data/sentence_draft.tsv  id, de, level, ko, model

같은 독일어 원문은 한 번만 번역한다. id는 원문의 해시이고, 학습 등급은 그
문장을 참조하는 단어 가운데 가장 낮은 등급이다. 이미 저장된 id는 건너뛰므로
중간에 끊겨도 다시 실행하면 이어진다.

실행  python scripts/04_sentences.py --workers 4
      python scripts/04_sentences.py --levels a1 --limit 60 --dry-run
"""
from __future__ import annotations

import argparse
import json

from pydantic import BaseModel, ConfigDict

from common import LEVELS, SENTENCE_DRAFT, WORDLIST, log, read_jsonl, read_tsv, write_tsv
from ids import unique_sentences
from llm import pick_backend, run_chunks

CHUNK = 60
SDK_MODEL = "claude-sonnet-4-5"
DRAFT_FIELDS = ["id", "de", "level", "ko", "model"]

SYSTEM = """\
너는 독일어-한국어 학습 자료의 번역자다. 괴테 인스티투트 A1~B1 예문을 자연스럽고 짧은 한국어로 옮긴다.

번역 규칙
- 뜻을 빠뜨리거나 설명을 덧붙이지 말고, 학습자가 원문 구조를 알아볼 수 있게 번역한다.
- 말투는 해요체로 통일한다. 원문에 du가 있을 때만 반말로 쓴다.
  Sie도 이름 부르기도 없는 평서문은 해요체다.
- 괄호로 대안을 나열하지 않는다. 문맥이 부족해도 가장 자연스러운 뜻 하나를 고른다.
  Bruder는 문맥이 없으면 '형제'나 '(오빠/남동생)'처럼 쓰지 말고 '형'으로 쓴다.
- 독일어 원문, 영어 번역, 해설은 ko에 되풀이하지 않는다.

출력은 스키마대로 JSON만 쓴다. id는 입력 그대로 돌려주고, 항목을 빼거나 더하지 않는다."""


class SentenceItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    ko: str


class SentenceBatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[SentenceItem]


def build_prompt(entries: list[dict]) -> str:
    items = [
        {"id": entry["id"], "de": entry["de"], "en": entry["en"], "level": entry["level"].upper()}
        for entry in entries
    ]
    return f"다음 {len(items)}개 독일어 예문의 ko를 써라.\n" + json.dumps(items, ensure_ascii=False, indent=1)


def read_drafts() -> list[dict]:
    """중단된 두 실행이 겹쳤을 때도 id당 첫 성공 응답 하나만 남긴다."""
    rows = read_tsv(SENTENCE_DRAFT)
    unique = []
    seen = set()
    for row in rows:
        if row["id"] not in seen:
            unique.append(row)
            seen.add(row["id"])
    if len(unique) != len(rows):
        write_tsv(SENTENCE_DRAFT, unique, DRAFT_FIELDS)
        log(f"sentences: removed {len(rows) - len(unique)} duplicate draft rows")
    return unique


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--levels", default=",".join(LEVELS))
    ap.add_argument("--backend", choices=["auto", "sdk", "cli", "codex"], default="auto")
    ap.add_argument("--model", default=None, help="sdk 기본 claude-sonnet-4-5, cli 기본은 Claude Code 설정값")
    ap.add_argument("--effort", choices=["low", "medium", "high", "max"], default="low")
    ap.add_argument("--workers", type=int, default=4, help="동시에 보낼 요청 수")
    ap.add_argument("--chunk", type=int, default=CHUNK)
    ap.add_argument("--limit", type=int, default=None, help="처음 N개만 (시험용)")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    levels = {level.strip().lower() for level in args.levels.split(",") if level.strip()}
    all_sentences = unique_sentences(read_jsonl(WORDLIST))
    entries = [entry for entry in all_sentences if entry["level"] in levels]
    done = {row["id"] for row in read_drafts()}
    todo = [entry for entry in entries if entry["id"] not in done]
    if args.limit is not None:
        todo = todo[:args.limit]
    chunks = [todo[i:i + args.chunk] for i in range(0, len(todo), args.chunk)]
    log(
        f"sentences: {len(entries)} entries in {sorted(levels)}, {len(done)} already drafted, "
        f"{len(todo)} to do in {len(chunks)} chunks"
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

    new_file = not SENTENCE_DRAFT.exists()
    fh = SENTENCE_DRAFT.open("a", encoding="utf-8")
    if new_file:
        fh.write("\t".join(DRAFT_FIELDS) + "\n")
    by_id = {entry["id"]: entry for entry in todo}

    def save(items: list[SentenceItem], used: str) -> None:
        for item in items:
            entry = by_id[item.id]
            row = [item.id, entry["de"], entry["level"], item.ko.strip(), used]
            fh.write("\t".join(cell.replace("\t", " ").replace("\n", " ") for cell in row) + "\n")
        fh.flush()

    try:
        run_chunks(
            todo,
            label="sentences",
            system=SYSTEM,
            build_prompt=build_prompt,
            batch_type=SentenceBatch,
            valid_item=lambda item: bool(item.ko.strip()),
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
    log(f"sentences: → {SENTENCE_DRAFT}")


if __name__ == "__main__":
    main()
