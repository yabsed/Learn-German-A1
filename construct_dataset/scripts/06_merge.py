"""6단계: 앞 단계 산출물을 앱이 읽는 words.json과 sentences.json으로 합친다.

입력  data/wordlist.jsonl   data/ipa.jsonl   data/ko_draft.tsv
      data/sentence_draft.tsv   data/gloss_draft.jsonl
      data/gloss_overrides.jsonl   data/overrides.tsv
출력  data/words.json
        {"id": "vater", "de": "der Vater", "lemma": "Vater", ...,
         "examples": [{"id": "s...", "de": "Mein Vater ist Arbeiter.", "en": "..."}]}
      data/sentences.json
        {"id": "s...", "de": "Mein Vater ist Arbeiter.", "en": "...",
         "ko": "제 아버지는 노동자예요.", "level": "A1"}
      data/review_queue.tsv  사람이 봐야 할 단어
      data/stats.json        단어·예문 등급별 개수와 커버리지

복수형은 괴테 목록의 힌트를 편 것을 쓰고, 힌트가 없거나 못 푼 것은
위키낱말사전 것을 쓴다. 둘 다 있는데 다르면 검수 목록에 올린다.

실행  python scripts/06_merge.py
"""
from __future__ import annotations

import json
import re
from collections import Counter, defaultdict

from common import (
    DATA,
    GLOSS_DRAFT,
    GLOSS_OVERRIDES,
    GLOSS_REVIEW,
    IPA,
    KO_DRAFT,
    OVERRIDES,
    REVIEW,
    SENTENCE_DRAFT,
    SENTENCES,
    WORDLIST,
    WORDS,
    log,
    read_jsonl,
    read_tsv,
    write_tsv,
)
from ids import sentence_id, unique_sentences

FORM_RE = re.compile(r"[A-Za-zÄÖÜäöüß]+")
GLOSS_TOKEN_RE = re.compile(r"(?:\([A-Za-zÄÖÜäöüß]+\))?[A-Za-zÄÖÜäöüß]+(?:[-/][A-Za-zÄÖÜäöüß]+)*|\d+(?:[.,:]\d+)*")


def optional_jsonl(path) -> list[dict]:
    return read_jsonl(path) if path.exists() else []


def gloss_reasons(sentence: dict, gloss: dict | None) -> list[str]:
    """잘못된 정렬은 앱에 싣지 않고, 의심스러운 정렬은 검수 목록에 올린다."""
    if not gloss:
        return ["no_gloss"]
    pairs = gloss.get("g")
    if not isinstance(pairs, list) or not pairs:
        return ["invalid_gloss"]
    reasons = []
    total = 0
    for pair in pairs:
        if not isinstance(pair, list) or len(pair) != 2:
            return ["invalid_gloss"]
        span, meaning = pair
        if not isinstance(span, int) or not 0 < span <= 3 or not isinstance(meaning, str) or not meaning.strip():
            return ["invalid_gloss"]
        total += span
        if span > 1:
            reasons.append("multiword")
        if len(meaning.strip()) > 15:
            reasons.append("long_meaning")
    if total != len(GLOSS_TOKEN_RE.findall(sentence["de"])):
        return [f"span_mismatch={total}/{len(GLOSS_TOKEN_RE.findall(sentence['de']))}"]
    return list(dict.fromkeys(reasons))


def variants(entry: dict, plural: str | None) -> list[str]:
    """Return only source-declared forms that can safely resolve to this entry.

    The Goethe ``forms`` field contains short paradigms (including separated
    verbs).  Keeping its individual words supports links such as ``ruft`` →
    ``anrufen`` and ``gefahren`` → ``losfahren`` without guessing from a stem.
    """
    forms = [entry["lemma"]]
    if plural:
        forms.append(plural)
    forms.extend(FORM_RE.findall(entry.get("forms") or ""))
    return list(dict.fromkeys(form for form in forms if len(form) > 1))


def main() -> None:
    entries = read_jsonl(WORDLIST)
    ipa = {row["id"]: row for row in read_jsonl(IPA)} if IPA.exists() else {}
    draft = {row["id"]: row for row in read_tsv(KO_DRAFT)}
    sentence_draft = {row["id"]: row for row in read_tsv(SENTENCE_DRAFT)}
    gloss_draft = {row["id"]: row for row in optional_jsonl(GLOSS_DRAFT)}
    gloss_overrides = {row["id"]: row for row in optional_jsonl(GLOSS_OVERRIDES)}
    overrides = {
        row["id"]: {key: value.strip() for key, value in row.items() if key != "id" and value and value.strip()}
        for row in read_tsv(OVERRIDES)
    }

    words, review = [], []
    stats = defaultdict(Counter)
    for entry in entries:
        level = entry["level"]
        stats[level]["entries"] += 1
        pronunciation = ipa.get(entry["id"], {})
        override = overrides.get(entry["id"], {})
        ko_row = draft.get(entry["id"]) or {}
        reasons = []
        plural_only = entry.get("number") == "pl"

        article = override.get("article") or entry["article"]
        de = re.sub(r"^(der|die|das) ", article + " ", entry["de"]) if override.get("article") else entry["de"]
        plural = override.get("plural") or entry["plural"]
        wikt_plurals = pronunciation.get("wikt_plurals") or []
        wikt_articles = pronunciation.get("wikt_articles") or []
        if plural_only:
            plural = None
        elif plural is None and wikt_plurals:
            plural = wikt_plurals[0]
            stats[level]["plural_from_wikt"] += 1
        elif (
            plural
            and wikt_plurals
            and not override.get("plural")
            and plural not in wikt_plurals
            and not (plural.endswith("n") and plural[:-1] in wikt_plurals)
        ):
            reasons.append(f"plural_mismatch goethe={plural} wikt={'/'.join(wikt_plurals)}")
            stats[level]["plural_mismatch"] += 1
        if (
            article
            and wikt_articles
            and not plural_only
            and not override.get("article")
            and article not in wikt_articles
        ):
            reasons.append(f"article_mismatch goethe={article} wikt={'/'.join(wikt_articles)}")
            stats[level]["article_mismatch"] += 1

        ipa_value = override.get("ipa") or pronunciation.get("ipa")
        if ipa_value:
            stats[level]["ipa"] += 1
        else:
            reasons.append("no_ipa")
        ko = override.get("ko") or ko_row.get("ko")
        note = override.get("note") if "note" in override else ko_row.get("note", "")
        if ko:
            stats[level]["ko"] += 1
        else:
            reasons.append("no_ko")
        for key in override:
            if key != "de":
                stats[level][f"override_{key}"] += 1

        words.append(
            {
                "id": entry["id"],
                "de": de,
                "lemma": entry["lemma"],
                "article": article,
                "plural": (f"die {plural}" if plural else None),
                "variants": variants(entry, plural),
                "level": level.upper(),
                "ipa": ipa_value,
                "ko": ko or None,
                "note": note or "",
                "pos": pronunciation.get("pos_title"),
                "examples": [
                    {"id": sentence_id(example["de"]), "de": example["de"], "en": example["en"]}
                    for example in entry["examples"]
                ],
            }
        )
        if reasons:
            review.append(
                {
                    "id": entry["id"],
                    "de": de,
                    "level": level,
                    "ipa": ipa_value or "",
                    "ko": ko or "",
                    "reasons": "; ".join(reasons),
                }
            )

    sentences, gloss_review = [], []
    sentence_stats = defaultdict(Counter)
    for sentence in unique_sentences(entries):
        level = sentence["level"]
        ko = (sentence_draft.get(sentence["id"]) or {}).get("ko")
        gloss = gloss_overrides.get(sentence["id"]) or gloss_draft.get(sentence["id"])
        gloss_issues = gloss_reasons(sentence, gloss)
        valid_gloss = gloss is not None and not any(
            reason.startswith(("no_gloss", "invalid_gloss", "span_mismatch")) for reason in gloss_issues
        )
        sentence_stats[level]["entries"] += 1
        if ko:
            sentence_stats[level]["ko"] += 1
        if valid_gloss:
            sentence_stats[level]["gloss"] += 1
        output = {
            "id": sentence["id"],
            "de": sentence["de"],
            "en": sentence["en"],
            "ko": ko or None,
            "level": level.upper(),
        }
        if valid_gloss:
            output["g"] = gloss["g"]
        sentences.append(output)
        if gloss_issues:
            gloss_review.append({
                "id": sentence["id"],
                "level": level,
                "de": sentence["de"],
                "ko": ko or "",
                "reasons": "; ".join(gloss_issues),
            })

    WORDS.write_text(json.dumps(words, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    SENTENCES.write_text(json.dumps(sentences, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    write_tsv(
        REVIEW,
        review,
        ["id", "de", "level", "ipa", "ko", "reasons"],
        "사람이 봐야 할 항목. 고칠 것은 overrides.tsv 에 같은 id 로 적는다. 다시 merge 하면 여기서 사라진다.",
    )
    write_tsv(
        GLOSS_REVIEW,
        gloss_review,
        ["id", "level", "de", "ko", "reasons"],
        "문맥 주석이 없거나 사람이 먼저 확인할 예문. 고친 값은 gloss_overrides.jsonl에 같은 id로 적는다.",
    )
    keys = sorted({key for counter in stats.values() for key in counter})
    total = {key: sum(counter[key] for counter in stats.values()) for key in keys}
    sentence_total = sum(counter["entries"] for counter in sentence_stats.values())
    sentence_ko = sum(counter["ko"] for counter in sentence_stats.values())
    sentence_gloss = sum(counter["gloss"] for counter in sentence_stats.values())
    out = {
        "total": total,
        "by_level": {level: dict(counter) for level, counter in sorted(stats.items())},
        "sentences": {
            "entries": sentence_total,
            "ko": sentence_ko,
            "gloss": sentence_gloss,
            "by_level": {
                level: {"entries": counter["entries"], "ko": counter["ko"], "gloss": counter["gloss"]}
                for level, counter in sorted(sentence_stats.items())
            },
        },
        "gloss_review_queue": len(gloss_review),
        "review_queue": len(review),
        "review_reasons": dict(
            Counter(reason.split()[0] for row in review for reason in row["reasons"].split("; "))
        ),
    }
    (DATA / "stats.json").write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

    log(f"merge: {len(words)} words → {WORDS}")
    log(f"       {len(sentences)} sentences ({sentence_ko} ko, {sentence_gloss} glossed) → {SENTENCES}")
    for level, counter in sorted(stats.items()):
        count = counter["entries"]
        log(
            f"  {level}: {count} entries, ipa {counter['ipa']} ({100 * counter['ipa'] / count:.1f}%), "
            f"ko {counter['ko']} ({100 * counter['ko'] / count:.1f}%), "
            f"plural mismatch {counter['plural_mismatch']}, article mismatch {counter['article_mismatch']}"
        )
    log(f"  review queue: {len(review)} → {REVIEW}   reasons: {out['review_reasons']}")


if __name__ == "__main__":
    main()
