"""행간 주석의 독일어 표현을 안정적인 오디오 id와 연결한다."""
from __future__ import annotations

import hashlib
import re
import unicodedata
from collections.abc import Iterable

from piper_tts import DEFAULT_VOICE

GLOSS_TOKEN_RE = re.compile(
    r"(?:\([A-Za-zÄÖÜäöüß]+\))?[A-Za-zÄÖÜäöüß]+"
    r"(?:[-/][A-Za-zÄÖÜäöüß]+)*|\d+(?:[.,:]\d+)*"
)

# 이 값을 바꾸면 같은 표현도 새 URL을 얻는다. 음성·속도·인코딩을 바꿀 때
# profile도 함께 올려 오래된 서비스 워커 캐시와 섞이지 않게 한다.
GLOSS_AUDIO_SCALE = 1.25
GLOSS_AUDIO_BITRATE = "32k"
GLOSS_AUDIO_PROFILE = f"{DEFAULT_VOICE}_{GLOSS_AUDIO_SCALE}_{GLOSS_AUDIO_BITRATE}_v1"


def gloss_audio_id(spoken: str, profile: str = GLOSS_AUDIO_PROFILE) -> str:
    normalized = unicodedata.normalize("NFC", spoken)
    payload = f"{profile}\0{normalized}".encode("utf-8")
    return "g" + hashlib.sha256(payload).hexdigest()[:12]


def gloss_audio_pairs(text: str, gloss: list[list]) -> list[tuple[int, str, str, str]]:
    """(span, 뜻, audio id, 발음할 독일어)를 주석 순서대로 돌려준다."""
    tokens = list(GLOSS_TOKEN_RE.finditer(text))
    at = 0
    pairs = []
    for pair in gloss:
        span, meaning = pair[:2]
        spoken = " ".join(match.group(0) for match in tokens[at:at + span])
        if not spoken or len(tokens[at:at + span]) != span:
            raise ValueError(f"invalid gloss span in {text!r}: {pair!r}")
        audio_id = gloss_audio_id(spoken)
        if len(pair) >= 3 and pair[2] != audio_id:
            raise ValueError(f"stale gloss audio id in {text!r}: {pair[2]!r} != {audio_id!r}")
        pairs.append((span, meaning, audio_id, spoken))
        at += span
    if at != len(tokens):
        raise ValueError(f"gloss does not cover {text!r}: {at}/{len(tokens)}")
    return pairs


def attach_gloss_audio(text: str, gloss: list[list]) -> list[list]:
    return [[span, meaning, audio_id] for span, meaning, audio_id, _ in gloss_audio_pairs(text, gloss)]


def unique_gloss_audio(sentences: Iterable[dict], levels: set[str]) -> list[tuple[str, str]]:
    """선택한 등급이 참조하는 고유한 (audio id, 발음 문자열)을 만든다."""
    by_id: dict[str, str] = {}
    for sentence in sentences:
        if sentence["level"].lower() not in levels or not sentence.get("g"):
            continue
        for _, _, audio_id, spoken in gloss_audio_pairs(sentence["de"], sentence["g"]):
            previous = by_id.setdefault(audio_id, spoken)
            if previous != spoken:
                raise ValueError(f"gloss audio id collision: {audio_id}: {previous!r} / {spoken!r}")
    return list(by_id.items())
