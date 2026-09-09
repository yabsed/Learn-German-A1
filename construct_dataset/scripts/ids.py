"""데이터셋의 id 규칙.

단어는 사람이 읽을 수 있어야 하므로 슬러그를 쓰고, 문장은 문장부호까지
구별해야 하므로 원문을 해시한다. 파일을 만드는 쪽은 이 id를 받아 쓸 뿐
텍스트에서 별도의 이름을 만들지 않는다.
"""
from __future__ import annotations

import hashlib
import re
import unicodedata

ASCII = str.maketrans(
    {"ä": "ae", "ö": "oe", "ü": "ue", "Ä": "ae", "Ö": "oe", "Ü": "ue", "ß": "ss"}
)
LEVEL_RANK = {"a1": 0, "a2": 1, "b1": 2}


def word_id(lemma: str) -> str:
    """단어 표제어를 안정적인 ASCII id로 바꾼다. 충돌 접미사는 호출자가 붙인다."""
    text = unicodedata.normalize("NFKD", lemma.translate(ASCII))
    text = text.encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-") or "x"


def sentence_id(de: str) -> str:
    """독일어 원문 그대로 해시한다. 문장부호·대소문자·공백도 id에 반영된다."""
    return "s" + hashlib.sha1(de.encode("utf-8")).hexdigest()[:10]


def unique_sentences(words: list[dict]) -> list[dict]:
    """단어 예문을 원문 기준으로 합치고 데이터셋 id와 학습 등급을 붙인다.

    한 문장이 여러 단어에 달렸다면 가장 낮은 단어 등급에서 먼저 학습한다.
    최초 영어 번역과 최초 등장 순서는 보존한다.
    """
    by_de: dict[str, dict] = {}
    by_id: dict[str, str] = {}
    for word in words:
        level = word["level"].lower()
        for example in word.get("examples", []):
            de = example["de"]
            sid = sentence_id(de)
            other = by_id.setdefault(sid, de)
            if other != de:
                raise ValueError(f"sentence id collision: {sid}: {other!r} / {de!r}")
            current = by_de.get(de)
            if current is None:
                by_de[de] = {
                    "id": sid,
                    "de": de,
                    "en": example.get("en", ""),
                    "level": level,
                }
            elif LEVEL_RANK[level] < LEVEL_RANK[current["level"]]:
                current["level"] = level
    return list(by_de.values())
