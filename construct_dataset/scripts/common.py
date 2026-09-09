"""데이터셋 스크립트가 공유하는 경로와 입출력 도우미.

모든 경로는 construct_dataset/ 를 기준으로 잡는다. 어느 디렉터리에서 실행해도 같은 파일을 본다.
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent  # construct_dataset/
DATA = ROOT / "data"
RAW = DATA / "raw"  # git 제외. 300 MB짜리 위키낱말사전 덤프가 여기 온다.
WORDLIST_REPO = ROOT / "third_party" / "goethe-institute-wordlist"

LEVELS = ("a1", "a2", "b1")
OVERRIDE_FIELDS = ["id", "de", "article", "plural", "ipa", "ko", "note"]

# 단계별 산출물. 앞 단계의 출력이 뒷 단계의 입력이다.
WORDLIST = DATA / "wordlist.jsonl"          # 1단계: 표제어·관사·복수형·등급·예문
KAIKKI_GZ = RAW / "raw-wiktextract-data.jsonl.gz"
KAIKKI_MATCHES = DATA / "kaikki_matches.jsonl"  # 2단계 중간: 덤프에서 건진 원본 항목(축약)
IPA = DATA / "ipa.jsonl"                    # 2단계: id → IPA
KO_DRAFT = DATA / "ko_draft.tsv"            # 3단계: 언어 모델이 쓴 단어 뜻 초안
SENTENCE_DRAFT = DATA / "sentence_draft.tsv"  # 4단계: 언어 모델이 쓴 예문 번역 초안
OVERRIDES = DATA / "overrides.tsv"          # 사람이 고친 것. 관사·복수형·IPA·뜻 어느 열이든 채우면 그것이 이긴다.
WORDS = DATA / "words.json"                 # 5단계: 앱이 읽는 최종 단어 파일
SENTENCES = DATA / "sentences.json"         # 5단계: 앱이 읽는 최종 예문 파일
REVIEW = DATA / "review_queue.tsv"          # 5단계: 사람이 봐야 할 단어 목록
AUDIO = DATA / "audio"                      # 6단계: words/sentences의 id.mp3


def log(*args: object) -> None:
    print(*args, file=sys.stderr, flush=True)


def read_jsonl(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def write_jsonl(path: Path, rows) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
            n += 1
    return n


def read_tsv(path: Path) -> list[dict]:
    """헤더가 있는 TSV. '#'으로 시작하는 줄과 빈 줄은 건너뛴다. 없으면 빈 목록."""
    if not path.exists():
        return []
    with path.open(encoding="utf-8", newline="") as f:
        lines = [ln for ln in f if ln.strip() and not ln.startswith("#")]
    if not lines:
        return []
    reader = csv.DictReader(lines, delimiter="\t", quoting=csv.QUOTE_NONE)
    return [dict(r) for r in reader]


def write_tsv(path: Path, rows: list[dict], fields: list[str], header_comment: str = "") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        if header_comment:
            for line in header_comment.strip().splitlines():
                f.write(f"# {line}\n")
        w = csv.DictWriter(f, fieldnames=fields, delimiter="\t", quoting=csv.QUOTE_NONE,
                           escapechar="\\", extrasaction="ignore", lineterminator="\n")
        w.writeheader()
        for r in rows:
            w.writerow({k: ("" if r.get(k) is None else str(r.get(k)).replace("\t", " ").replace("\n", " "))
                        for k in fields})
