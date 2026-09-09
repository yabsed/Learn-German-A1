"""3단계: 언어 모델이 한국어 뜻 초안을 쓴다. 검수는 사람이 overrides.tsv 에서 한다.

입력  data/wordlist.jsonl   (1단계)  표제어·등급·예문
      data/ipa.jsonl        (2단계, 있으면)  위키낱말사전 품사를 힌트로 같이 보낸다
출력  data/ko_draft.tsv     id, de, level, ko, note, model  — 모델 초안. 다시 돌리면 이미 있는 id 는 건너뛴다.
      data/overrides.tsv    사람이 고친 것. ko 열을 채우면 5단계에서 초안보다 우선한다. (관사·복수형·IPA 도 같은 파일)

백엔드
  sdk   Anthropic Python SDK.  ANTHROPIC_API_KEY (또는 ANTHROPIC_AUTH_TOKEN) 이 있을 때. 기본 모델 claude-opus-5.
  cli   로컬 Claude Code (`claude -p`). API 키 없이 구독으로 돌릴 때. 모델은 Claude Code 기본값.
  auto  키가 있으면 sdk, 없으면 cli.  (기본)

한 요청에 CHUNK 개 항목을 JSON 으로 보내고, 같은 개수의 {id, ko, note} 를 JSON 스키마로 강제해 받는다.
답에서 빠진 id 는 모아서 한 번 더 묻는다. 그래도 없으면 비워 두고 5단계의 검수 목록에 오른다.

실행  python scripts/03_ko.py                          # 전체, auto 백엔드
      python scripts/03_ko.py --levels a1 --workers 4
      python scripts/03_ko.py --backend sdk --model claude-opus-5
      python scripts/03_ko.py --dry-run                # 첫 묶음의 프롬프트만 찍는다
"""
from __future__ import annotations

import argparse
import json
from pydantic import BaseModel, ConfigDict

from common import IPA, KO_DRAFT, OVERRIDES, OVERRIDE_FIELDS, LEVELS, WORDLIST, log, read_jsonl, read_tsv
from llm import pick_backend, run_chunks

CHUNK = 60
SDK_MODEL = "claude-opus-5"
DRAFT_FIELDS = ["id", "de", "level", "ko", "note", "model"]

SYSTEM = """\
너는 독일어-한국어 학습용 단어장의 편집자다. 괴테 인스티투트 A1~B1 단어 목록의 항목을 JSON으로 받아
각 항목에 한국어 뜻(ko)과 짧은 메모(note)를 단다.

ko 규칙
- 사전 표제어처럼 짧게. 문장이나 설명이 아니라 뜻만. 흔한 뜻 1~3개를 쉼표로 구분한다.
  예: "아버지" / "데리러 가다, 찾아오다" / "오래된, 늙은"
- 예문에 쓰인 뜻을 반드시 넣고, 예문이 여러 개면 그 뜻들을 앞에 둔다.
- 명사는 명사형, 동사는 '-다' 기본형, 형용사는 '-한/-ㄴ' 꼴, 부사·전치사·접속사는 기능이 드러나는
  우리말("~부터", "그러나", "아마도").
- 독일어 단어, 관사, 복수형, 괄호 설명은 ko에 쓰지 않는다.

note 규칙
- 학습자가 꼭 알아야 할 것만 20자 이내. 예: "재귀동사", "복수형만 씀", "분리동사", "구어",
  "예문은 관용구", "장소 이동은 4격". 없으면 빈 문자열.

출력은 스키마대로 JSON만. id는 입력 그대로 돌려주고, 항목을 빼거나 더하지 않는다."""

class KoItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    ko: str
    note: str = ""


class KoBatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[KoItem]


def build_prompt(entries: list[dict], pos_hint: dict[str, str]) -> str:
    items = []
    for e in entries:
        item = {"id": e["id"], "de": e["de"], "level": e["level"].upper()}
        if e.get("forms"):
            item["forms"] = e["forms"]
        if pos_hint.get(e["id"]):
            item["pos"] = pos_hint[e["id"]]
        item["examples"] = [{"de": x["de"], "en": x["en"]} for x in e["examples"][:4]]
        items.append(item)
    return f"다음 {len(items)}개 항목의 ko와 note를 써라.\n" + json.dumps(items, ensure_ascii=False, indent=1)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--levels", default=",".join(LEVELS))
    ap.add_argument("--backend", choices=["auto", "sdk", "cli", "codex"], default="auto")
    ap.add_argument("--model", default=None, help="sdk 기본 claude-opus-5, cli 기본은 Claude Code 설정값")
    ap.add_argument("--effort", choices=["low", "medium", "high", "max"], default=None)
    ap.add_argument("--workers", type=int, default=2, help="동시에 보낼 요청 수")
    ap.add_argument("--chunk", type=int, default=CHUNK)
    ap.add_argument("--limit", type=int, default=None, help="처음 N 항목만 (시험용)")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    levels = {l.strip().lower() for l in args.levels.split(",")}
    entries = [e for e in read_jsonl(WORDLIST) if e["level"] in levels]
    done = {r["id"] for r in read_tsv(KO_DRAFT)}
    todo = [e for e in entries if e["id"] not in done]
    if args.limit is not None:
        todo = todo[:args.limit]
    pos_hint = {r["id"]: r["pos_title"] for r in read_jsonl(IPA) if r.get("pos_title")} if IPA.exists() else {}
    chunks = [todo[i:i + args.chunk] for i in range(0, len(todo), args.chunk)]
    log(f"ko: {len(entries)} entries in {sorted(levels)}, {len(done)} already drafted, {len(todo)} to do in {len(chunks)} chunks")

    if args.dry_run:
        if chunks:
            print(build_prompt(chunks[0], pos_hint))
        return
    if not chunks:
        return

    backend = pick_backend(args.backend)
    model_label = args.model or (SDK_MODEL if backend == "sdk" else f"{backend}-default")
    log(f"  backend={backend} model={model_label} workers={args.workers}")

    if not OVERRIDES.exists():
        OVERRIDES.write_text(
            "# 사람이 고친 것. 5단계에서 자동 생성값보다 우선한다. 빈 칸은 무시. de 는 참고용.\n"
            "# plural 은 관사 없이 (Väter), ipa 는 대괄호 없이 (ˈfaːtɐ).\n"
            + "\t".join(OVERRIDE_FIELDS) + "\n", encoding="utf-8")

    new_file = not KO_DRAFT.exists()
    fh = KO_DRAFT.open("a", encoding="utf-8")
    if new_file:
        fh.write("\t".join(DRAFT_FIELDS) + "\n")
    by_id = {e["id"]: e for e in todo}

    def save(items: list[KoItem], used: str) -> None:
        for it in items:
            e = by_id[it.id]
            row = [it.id, e["de"], e["level"], it.ko.strip(), it.note.strip(), used]
            fh.write("\t".join(c.replace("\t", " ").replace("\n", " ") for c in row) + "\n")
        fh.flush()

    try:
        run_chunks(
            todo,
            label="ko",
            system=SYSTEM,
            build_prompt=lambda chunk: build_prompt(chunk, pos_hint),
            batch_type=KoBatch,
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
    log(f"ko: → {KO_DRAFT}")


if __name__ == "__main__":
    main()
