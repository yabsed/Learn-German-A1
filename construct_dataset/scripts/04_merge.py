"""4단계: 1~3단계 산출물을 하나로 합쳐 앱이 읽을 words.json 을 만든다.

입력  data/wordlist.jsonl   data/ipa.jsonl   data/ko_draft.tsv   data/overrides.tsv
출력  data/words.json        항목 하나는 이런 모양이다.
        {"id": "vater", "de": "der Vater", "lemma": "Vater", "article": "der", "plural": "die Väter",
         "level": "A1", "ipa": "ˈfaːtɐ", "ko": "아버지", "note": "", "pos": "Substantiv",
         "examples": [{"de": "Mein Vater ist Arbeiter.", "en": "My father is a worker."}]}
      data/review_queue.tsv  사람이 봐야 할 항목. 이유 열에 no_ipa / no_ko / plural_mismatch / article_mismatch.
                             고칠 것은 data/overrides.tsv 에 적는다. 열 하나만 채워도 된다.
      data/stats.json        등급별 개수와 커버리지. 보고서용.

복수형은 괴테 목록의 힌트를 편 것을 쓰고, 힌트가 없거나 못 푼 것은 위키낱말사전 것을 쓴다.
둘 다 있는데 다르면 검수 목록에 올린다. 어느 쪽이 맞는지는 사람이 본다.

실행  python scripts/04_merge.py
"""
from __future__ import annotations

import json
from collections import Counter, defaultdict

import re

from common import IPA, KO_DRAFT, OVERRIDES, REVIEW, WORDLIST, WORDS, DATA, log, read_jsonl, read_tsv, write_tsv


def main() -> None:
    entries = read_jsonl(WORDLIST)
    ipa = {r["id"]: r for r in read_jsonl(IPA)} if IPA.exists() else {}
    draft = {r["id"]: r for r in read_tsv(KO_DRAFT)}
    overrides = {r["id"]: {k: v.strip() for k, v in r.items() if k != "id" and v and v.strip()}
                 for r in read_tsv(OVERRIDES)}

    words, review = [], []
    stats = defaultdict(Counter)
    for e in entries:
        lvl = e["level"]
        stats[lvl]["entries"] += 1
        p = ipa.get(e["id"], {})
        ov = overrides.get(e["id"], {})
        ko_row = draft.get(e["id"]) or {}
        reasons = []
        plural_only = e.get("number") == "pl"            # die Geschwister (Pl.): 관사 die 는 복수 관사다

        article = ov.get("article") or e["article"]
        de = re.sub(r"^(der|die|das) ", article + " ", e["de"]) if ov.get("article") else e["de"]
        plural = ov.get("plural") or e["plural"]
        wikt_plurals = p.get("wikt_plurals") or []
        wikt_articles = p.get("wikt_articles") or []
        if plural_only:
            plural = None
        elif plural is None and wikt_plurals:
            plural = wikt_plurals[0]
            stats[lvl]["plural_from_wikt"] += 1
        elif plural and wikt_plurals and not ov.get("plural") and plural not in wikt_plurals \
                and not (plural.endswith("n") and plural[:-1] in wikt_plurals):   # die Beamten / Beamte 는 같은 말
            reasons.append(f"plural_mismatch goethe={plural} wikt={'/'.join(wikt_plurals)}")
            stats[lvl]["plural_mismatch"] += 1
        if article and wikt_articles and not plural_only and not ov.get("article") and article not in wikt_articles:
            reasons.append(f"article_mismatch goethe={article} wikt={'/'.join(wikt_articles)}")
            stats[lvl]["article_mismatch"] += 1

        ipa_val = ov.get("ipa") or p.get("ipa")
        if ipa_val:
            stats[lvl]["ipa"] += 1
        else:
            reasons.append("no_ipa")
        ko = ov.get("ko") or ko_row.get("ko")
        note = ov.get("note") if "note" in ov else ko_row.get("note", "")
        if ko:
            stats[lvl]["ko"] += 1
        else:
            reasons.append("no_ko")
        for k in ov:
            if k != "de":
                stats[lvl][f"override_{k}"] += 1

        words.append({
            "id": e["id"],
            "de": de,
            "lemma": e["lemma"],
            "article": article,
            "plural": (f"die {plural}" if plural else None),
            "level": lvl.upper(),
            "ipa": ipa_val,
            "ko": ko or None,
            "note": note or "",
            "pos": p.get("pos_title"),
            "examples": [{"de": x["de"], "en": x["en"]} for x in e["examples"]],
        })
        if reasons:
            review.append({"id": e["id"], "de": de, "level": lvl, "ipa": ipa_val or "",
                           "ko": ko or "", "reasons": "; ".join(reasons)})

    WORDS.write_text(json.dumps(words, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    write_tsv(REVIEW, review, ["id", "de", "level", "ipa", "ko", "reasons"],
              "사람이 봐야 할 항목. 고칠 것은 overrides.tsv 에 같은 id 로 적는다. 다시 merge 하면 여기서 사라진다.")
    keys = sorted({k for c in stats.values() for k in c})
    total = {k: sum(c[k] for c in stats.values()) for k in keys}
    out = {"total": total, "by_level": {l: dict(c) for l, c in sorted(stats.items())}, "review_queue": len(review),
           "review_reasons": dict(Counter(r.split()[0] for row in review for r in row["reasons"].split("; ")))}
    (DATA / "stats.json").write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

    log(f"merge: {len(words)} words → {WORDS}")
    for l, c in sorted(stats.items()):
        n = c["entries"]
        log(f"  {l}: {n} entries, ipa {c['ipa']} ({100 * c['ipa'] / n:.1f}%), ko {c['ko']} ({100 * c['ko'] / n:.1f}%),"
            f" plural mismatch {c['plural_mismatch']}, article mismatch {c['article_mismatch']}")
    log(f"  review queue: {len(review)} → {REVIEW}   reasons: {out['review_reasons']}")


if __name__ == "__main__":
    main()
