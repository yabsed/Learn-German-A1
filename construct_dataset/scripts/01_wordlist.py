"""1단계: 괴테 Wortliste TSV → data/wordlist.jsonl

입력  third_party/goethe-institute-wordlist/{a1,a2,b1}/[a-z].tsv
      열은 셋이다. 표제어 \t 독일어 예문 \t 영어 번역. (b1의 일부 파일에만 헤더 줄이 있다.)
      표제어에는 관사·복수형 힌트·동사 변화형·뜻 번호가 한 문자열에 섞여 있다.
        der Vater, -ä          die Adresse,-en        das Buch, -ü, er(1)
        der Apfel, ¨-          abholen(2)             (sich) vorstellen
        sein, ist, war, ist gewesen                   gut, besser, am besten
출력  표제어 하나에 한 줄. 같은 표제어의 뜻 번호 (1)(2)…는 예문만 모아서 하나로 합친다.
      두 등급에 모두 나오는 단어는 낮은 등급 하나로 합치고 levels 에 둘 다 적는다.

실행  python scripts/01_wordlist.py [--levels a1,a2,b1]
"""
from __future__ import annotations

import argparse
import re
from collections import OrderedDict

from common import LEVELS, WORDLIST, WORDLIST_REPO, log, write_jsonl
from ids import word_id

ARTICLES = ("der", "die", "das")
SENSE_RE = re.compile(r"\s*\((\d+)\)\s*$")                     # abholen(2)
NUMBER_RE = re.compile(r"\s*\((Sg|Pl)\.?\)", re.I)             # Achtung (Sg.)  die Eltern (Pl.)
REGION_RE = re.compile(r"\s*\((?:D|A|CH)(?:\s*,\s*(?:D|A|CH))*\)")  # (D, CH)
TWO_NOUNS_RE = re.compile(r"^(der|die|das)\s+(.+?)\s*/\s*(der|die|das)\s+(.+)$")  # die Ehefrau, -en/der Ehemann, -ä, er
# 복수형 힌트. ¨ 는 움라우트, -ä/-ö/-ü 도 움라우트, 그 뒤가 어미.  -n  -e  ¨-e  -¨e  ¨  -ä, er  -
PLURAL_RE = re.compile(r"^(?:(?P<uml>¨)\s*-?|-\s*(?P<uml2>¨)?)\s*(?P<vow>[äöüÄÖÜ])?(?:\s*,\s*)?(?P<suf>[a-zäöüß]*)$")
FULL_PLURAL_RE = re.compile(r"^[A-ZÄÖÜ][a-zäöüß]+$")           # das Studium, Studien
DROP_PAREN_RE = re.compile(r"\((?:sich(?: etwas)?|etwas|jemanden|jemandem|ein)\)\s*")

DROPPED: list[str] = []   # 예문 없는 조각 줄. 실행 끝에 찍어 준다.
UMLAUT = {"a": "ä", "o": "ö", "u": "ü", "A": "Ä", "O": "Ö", "U": "Ü"}


def umlaut(stem: str) -> str | None:
    """마지막 a/o/u/au 에 움라우트를 찍는다. Vater→Väter, Baum→Bäum(e), Bahnhof→Bahnhöf(e)."""
    for i in range(len(stem) - 1, -1, -1):
        ch = stem[i]
        if ch == "u" and i > 0 and stem[i - 1] in "aA":
            return stem[: i - 1] + UMLAUT[stem[i - 1]] + "u" + stem[i + 1:]
        if ch in UMLAUT:
            return stem[:i] + UMLAUT[ch] + stem[i + 1:]
    return None


def expand_plural(lemma: str, hint: str) -> str | None:
    """'-ä, e' 같은 힌트를 실제 복수형으로 편다. 못 풀면 None.

    '-s/-n' 처럼 둘을 적어 둔 것은 앞의 것을, '¨- → Kiste' 같은 참조 표시는 떼고 본다.
    """
    hint = re.sub(r"\s*(→|->).*$", "", hint)
    hint = hint.replace("–", "-").replace("—", "-").strip()

    def build(m: "re.Match[str]") -> str | None:
        stem = lemma
        if m.group("uml") or m.group("uml2") or m.group("vow"):
            stem = umlaut(lemma)
            if stem is None:
                return None
        return join_suffix(stem, m.group("suf"))

    for part in re.split(r"\s*/\s*", hint):
        part = part.strip()
        if not part:
            continue
        m = PLURAL_RE.match(part)
        if m:
            return build(m)
        first = part.split(",")[0].strip()          # 'der Ski, -, -er' → '-'
        m = PLURAL_RE.match(first)
        if m:
            return build(m)
        if FULL_PLURAL_RE.match(part):
            return part
        return None
    return None


def join_suffix(stem: str, suf: str) -> str:
    """어미를 붙인다. 목록은 -e 로 끝나는 말에도 '-en' 이라 적고, 라틴어계 어미는 갈아 끼워야 한다.

    Adresse+en → Adressen   Datum+en → Daten   Praktikum+a → Praktika
    Thema+en → Themen       Konto+en → Konten  Praxis+en → Praxen     Bäum+e → Bäume (aum 은 라틴어 어미가 아니다)
    """
    if not suf:
        return stem
    if stem.endswith("um") and not stem.endswith(("aum", "äum")) and (suf.startswith("e") or suf == "a"):
        return stem[:-2] + suf
    if stem.endswith(("a", "o")) and suf == "en":
        return stem[:-1] + suf
    if stem.endswith("is") and suf == "en":
        return stem[:-2] + suf
    if stem.endswith("e") and suf.startswith("e"):
        return stem + suf[1:]
    return stem + suf


def clean_lemma(text: str) -> str:
    """'(sich) vorstellen'→'vorstellen', '(ab)fahren'→'abfahren', '(Kredit)-Karte'→'Kreditkarte', E-Mail 은 그대로."""
    text = DROP_PAREN_RE.sub("", text)
    text = re.sub(r"\(([^)]{2,}?)-\)", r"(\1)", text)    # (Back-)Ofen: 괄호에 붙은 하이픈은 합성어 표시일 뿐
    text = re.sub(r"\(([^)]{2,}?)\)-", r"(\1)", text)    # (Kredit)-Karte.  (E-)Mail 의 한 글자 접두는 하이픈을 남긴다
    had_paren = "(" in text
    text = text.replace("(", "").replace(")", "")
    if had_paren:                                      # (Back-)Ofen → BackOfen → Backofen
        text = re.sub(r"(?<=[a-zäöüß])([A-ZÄÖÜ])(?=[a-zäöüß])", lambda m: m.group(1).lower(), text)
    return re.sub(r"\s+", " ", text).strip(" -")


def lookup_keys(lemma_part: str) -> list[str]:
    """위키낱말사전 대조에 쓸 후보를 우선순위대로. 앞의 것이 먼저 시도된다."""
    keys: list[str] = []

    def add(k: str) -> None:
        k = re.sub(r"\s+", " ", k).strip(" -")
        if k and k not in keys:
            keys.append(k)

    for alt in lemma_part.split("/"):
        add(clean_lemma(alt))
        add(re.sub(r"\([^)]*\)", "", alt))          # 괄호 안을 통째로 버린 꼴: (ab)fahren → fahren
        add(re.sub(r"\([^)]*\)", "", alt).replace("sich ", ""))
    return keys


def parse_headword(raw: str) -> list[dict]:
    """표제어 문자열 하나를 항목 dict 로. 드물게 두 표제어가 한 칸에 있어 list 를 돌려준다."""
    raw = raw.strip()
    m = SENSE_RE.search(raw)
    sense = int(m.group(1)) if m else None
    raw = SENSE_RE.sub("", raw)

    m2 = TWO_NOUNS_RE.match(raw)
    if m2:
        a, b = f"{m2.group(1)} {m2.group(2)}", f"{m2.group(3)} {m2.group(4)}"
        return [dict(e, sense=sense) for e in parse_headword(a) + parse_headword(b)]

    number = None
    if NUMBER_RE.search(raw):
        number = NUMBER_RE.search(raw).group(1).lower()
        raw = NUMBER_RE.sub("", raw)
    raw = REGION_RE.sub("", raw).strip()
    raw = re.sub(r"\s*(→|->).*$", "", raw)      # 'der Stock → D, CH: Etage' 같은 지역어 참조

    article = None
    body = raw
    m3 = re.match(r"^(der|die|das)\s+(.+)$", raw)
    if m3:
        article, body = m3.group(1), m3.group(2)

    lemma_part, _, hint = body.partition(",")
    lemma_part, hint = lemma_part.strip(), hint.strip()

    entry = {
        "de": (f"{article} {lemma_part}" if article else lemma_part),
        "lemma": clean_lemma(lemma_part.split("/")[0]),
        "article": article,
        "plural": None,
        "plural_hint": None,
        "forms": None,
        "number": number,
        "lookup_keys": lookup_keys(lemma_part),
        "sense": sense,
    }
    if article:
        entry["plural_hint"] = hint or None
        if hint:
            entry["plural"] = expand_plural(entry["lemma"], hint)
        elif number == "sg":
            entry["plural"] = None
    else:
        entry["forms"] = hint or None      # 동사 변화형이나 비교급이 여기 들어온다
    return [entry]


def read_level(level: str) -> list[tuple[dict, str, str]]:
    rows = []
    for path in sorted((WORDLIST_REPO / level).glob("[a-z].tsv")):
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip() or line.startswith("german word"):
                continue
            cols = line.split("\t")
            head, ex_de, ex_en = (cols + ["", ""])[:3]
            if not ex_de.strip():
                # PDF 를 옮기다 동사 변화형이 다음 줄로 넘어간 조각이다. "hat gechattet" 같은 것.
                DROPPED.append(f"{level}: {head.strip()}")
                continue
            for entry in parse_headword(head):
                rows.append((entry, ex_de.strip(), ex_en.strip()))
    return rows


def build(levels: list[str]) -> list[dict]:
    merged: "OrderedDict[tuple, dict]" = OrderedDict()
    for level in levels:
        for entry, ex_de, ex_en in read_level(level):
            key = (entry["lemma"].lower(), entry["article"])
            cur = merged.get(key)
            if cur is None:
                cur = dict(entry, level=level, levels=[level], examples=[])
                cur.pop("sense", None)
                merged[key] = cur
            else:
                # 같은 단어가 다시 나오면 빠진 정보만 채운다. 첫 등장(낮은 등급)의 표기가 이긴다.
                for k in ("plural", "plural_hint", "forms"):
                    if cur.get(k) is None and entry.get(k) is not None:
                        cur[k] = entry[k]
                for k in entry["lookup_keys"]:
                    if k not in cur["lookup_keys"]:
                        cur["lookup_keys"].append(k)
                if level not in cur["levels"]:
                    cur["levels"].append(level)
            if ex_de and not any(e["de"] == ex_de for e in cur["examples"]):
                cur["examples"].append({"de": ex_de, "en": ex_en, "level": level})

    # id: 등급이 아니라 단어에서 만든다. 등급이 바뀌어도 id 는 그대로여야 학습 기록이 살아남는다.
    seen: dict[str, int] = {}
    out = []
    for cur in merged.values():
        base = word_id(cur["lemma"])
        n = seen.get(base, 0) + 1
        seen[base] = n
        cur["id"] = base if n == 1 else f"{base}-{n}"
        out.append({k: cur[k] for k in ("id", "de", "lemma", "article", "plural", "plural_hint",
                                        "forms", "number", "level", "levels", "lookup_keys", "examples")})
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--levels", default=",".join(LEVELS), help="쉼표로 구분. 기본 a1,a2,b1")
    args = ap.parse_args()
    levels = [l.strip().lower() for l in args.levels.split(",") if l.strip()]
    if not (WORDLIST_REPO / "a1").exists():
        raise SystemExit(f"서브모듈이 비어 있다: git submodule update --init {WORDLIST_REPO.relative_to(WORDLIST_REPO.parent.parent)}")
    rows = build(levels)
    n = write_jsonl(WORDLIST, rows)
    by_level = {l: sum(1 for r in rows if r["level"] == l) for l in levels}
    nouns = sum(1 for r in rows if r["article"])
    with_plural = sum(1 for r in rows if r["plural"])
    unparsed = [r for r in rows if r["article"] and r["plural_hint"] and not r["plural"]]
    log(f"wordlist: {n} entries → {WORDLIST}")
    log(f"  by first level: {by_level}")
    log(f"  nouns {nouns}, plural expanded {with_plural}, plural hint unparsed {len(unparsed)}")
    for r in unparsed[:15]:
        log(f"    ? {r['de']}, {r['plural_hint']}")
    log(f"  dropped {len(DROPPED)} rows without an example sentence: {DROPPED}")


if __name__ == "__main__":
    main()
