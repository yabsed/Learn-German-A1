"""2단계: kaikki.org 독일어판 위키낱말사전 추출본에서 IPA 를 뽑는다.

입력  data/wordlist.jsonl                       (1단계 출력)
      data/raw/raw-wiktextract-data.jsonl.gz   (kaikki.org, 압축 303 MB, 풀면 2.8 GB — 풀지 않고 흘려 읽는다)
출력  data/kaikki_matches.jsonl   표제어와 겹치는 원본 항목만 축약해 둔 것. 덤프를 다시 안 받아도 되게.
      data/ipa.jsonl              id → ipa. 위키낱말사전이 아는 관사·복수형·Commons 녹음 URL 도 같이.

덤프 한 줄은 (표제어, 품사) 하나의 JSON 이다. 같은 철자가 여러 줄일 수 있다.
  sein   → 동사 / 소유대명사        Väter → 명사이지만 tags 에 form-of (변화형 페이지)
그래서 줄마다 점수를 매겨 하나를 고른다. 변화형 페이지는 감점, 관사가 있는 단어는 명사 우대.

실행  python scripts/02_ipa.py            # 덤프를 훑고(1~2분) 선택까지
      python scripts/02_ipa.py --reuse    # 덤프는 안 훑고 kaikki_matches.jsonl 에서 선택만 다시
"""
from __future__ import annotations

import argparse
import gzip
import json
import re
import time
from collections import defaultdict

from common import IPA, KAIKKI_GZ, KAIKKI_MATCHES, WORDLIST, log, read_jsonl, write_jsonl

WORD_RE = re.compile(r'"word":\s*"((?:[^"\\]|\\.)*)"')
GENDER_TO_ARTICLE = {"masculine": "der", "feminine": "die", "neuter": "das"}


def slim(rec: dict) -> dict:
    """한 줄 JSON 에서 우리가 쓸 것만 남긴다. 원본은 뜻풀이·어원·번역까지 있어 줄당 수 KB 다."""
    ipa = [s["ipa"] for s in rec.get("sounds", []) if s.get("ipa")]
    audio = [s["mp3_url"] for s in rec.get("sounds", []) if s.get("mp3_url")]
    plural, articles = [], []
    for f in rec.get("forms", []):
        tags = f.get("tags", [])
        if tags == ["nominative", "plural"] and f.get("form") and f["form"] not in plural:
            plural.append(f["form"])
        if tags == ["nominative", "singular"] and f.get("article") and f["article"] not in articles:
            articles.append(f["article"])     # der Beamte / die Beamte 처럼 둘일 수 있다
    if not articles:
        articles = [GENDER_TO_ARTICLE[t] for t in rec.get("tags", []) if t in GENDER_TO_ARTICLE]
    glosses = []
    for s in rec.get("senses", [])[:3]:
        g = s.get("glosses") or s.get("raw_glosses") or []
        if g:
            glosses.append(g[0][:120])
    return {
        "word": rec["word"],
        "pos": rec.get("pos"),
        "pos_title": rec.get("pos_title"),
        "tags": rec.get("tags", []),
        "ipa": ipa,
        "audio": audio,
        "articles": articles,
        "plurals": plural,
        "n_senses": len(rec.get("senses", [])),
        "glosses": glosses,
    }


def stream_matches(gz_path, wanted: set[str]):
    """덤프를 한 줄씩 흘려 읽으며 표제어가 wanted 에 있는 줄만 JSON 으로 푼다.

    2.8 GB 를 전부 json.loads 하면 몇 분이 걸린다. 줄 머리의 "word" 값만 정규식으로 먼저 보고,
    걸린 줄만 제대로 판다. 대부분의 줄은 첫 400자 안에 word 가 있다.
    """
    t0 = time.time()
    n_lines = n_hit = 0
    with gzip.open(gz_path, "rt", encoding="utf-8") as f:
        for line in f:
            n_lines += 1
            m = WORD_RE.search(line, 0, 400) or WORD_RE.search(line)
            if not m:
                continue
            w = m.group(1)
            if "\\" in w:
                w = json.loads(f'"{w}"')
            if w not in wanted:
                continue
            rec = json.loads(line)
            if rec.get("lang_code") != "de":
                continue
            n_hit += 1
            yield slim(rec)
            if n_lines % 200000 == 0:
                log(f"  … {n_lines:,} lines, {n_hit} matches, {time.time() - t0:.0f}s")
    log(f"  scanned {n_lines:,} lines in {time.time() - t0:.0f}s, {n_hit} German entries matched")


def clean_ipa(s: str) -> str | None:
    s = s.strip().strip("[]/").strip()
    if not s or "…" in s or "..." in s:
        return None
    return s


def score(entry: dict, rec: dict, key_rank: int) -> int:
    s = 0
    if "form-of" in rec["tags"]:
        s -= 100                     # Väter, möchten(변화형) 같은 페이지
    if any(clean_ipa(x) for x in rec["ipa"]):
        s += 20
    if entry["article"]:
        s += 10 if rec["pos"] == "noun" else 0
        if entry["article"] in rec["articles"]:
            s += 5
    elif rec["pos"] == "noun":
        s -= 2                       # 관사 없는 표제어가 명사 페이지와 겹치면 (Achtung) 약간만 밀어 둔다
    s += min(rec["n_senses"], 5)
    s -= 10 * key_rank               # lookup_keys 앞쪽 후보가 우선. Fahrrad/Rad 에서 Fahrrad 가 이겨야 한다
    return s


def choose(entry: dict, by_word: dict[str, list[dict]]) -> dict:
    cands = []
    for rank, key in enumerate(entry["lookup_keys"]):
        for rec in by_word.get(key, []):
            cands.append((score(entry, rec, rank), rec))
    if not cands:
        return {"id": entry["id"], "ipa": None, "matched_word": None}
    cands.sort(key=lambda t: -t[0])
    best = cands[0][1]
    ipas = []
    for _, rec in cands:
        for x in rec["ipa"]:
            c = clean_ipa(x)
            if c and c not in ipas:
                ipas.append(c)
    primary = next((clean_ipa(x) for x in best["ipa"] if clean_ipa(x)), None) or (ipas[0] if ipas else None)
    return {
        "id": entry["id"],
        "ipa": primary,
        "ipa_alts": [x for x in ipas if x != primary],
        "matched_word": best["word"],
        "pos": best["pos"],
        "pos_title": best["pos_title"],
        "wikt_articles": best["articles"],
        "wikt_plurals": best["plurals"],
        "audio": best["audio"],
        "glosses": best["glosses"],
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--reuse", action="store_true", help="덤프를 다시 훑지 않고 kaikki_matches.jsonl 을 쓴다")
    args = ap.parse_args()

    entries = read_jsonl(WORDLIST)
    wanted = {k for e in entries for k in e["lookup_keys"]}
    log(f"ipa: {len(entries)} entries, {len(wanted)} lookup keys")

    if args.reuse and KAIKKI_MATCHES.exists():
        matches = read_jsonl(KAIKKI_MATCHES)
        log(f"  reusing {len(matches)} cached matches from {KAIKKI_MATCHES}")
    else:
        if not KAIKKI_GZ.exists():
            raise SystemExit(f"덤프가 없다: make {KAIKKI_GZ.relative_to(KAIKKI_GZ.parents[2])}  (kaikki.org, 303 MB)")
        matches = list(stream_matches(KAIKKI_GZ, wanted))
        write_jsonl(KAIKKI_MATCHES, matches)

    by_word: dict[str, list[dict]] = defaultdict(list)
    for m in matches:
        by_word[m["word"]].append(m)

    rows = [choose(e, by_word) for e in entries]
    write_jsonl(IPA, rows)
    have = sum(1 for r in rows if r["ipa"])
    by_level = defaultdict(lambda: [0, 0])
    for e, r in zip(entries, rows):
        by_level[e["level"]][1] += 1
        by_level[e["level"]][0] += bool(r["ipa"])
    log(f"  IPA found for {have}/{len(rows)} → {IPA}")
    for lvl, (h, t) in sorted(by_level.items()):
        log(f"    {lvl}: {h}/{t} ({100 * h / t:.1f}%)")
    missing = [e["de"] for e, r in zip(entries, rows) if not r["ipa"]]
    log(f"  no IPA (first 20): {missing[:20]}")


if __name__ == "__main__":
    main()
