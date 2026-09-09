"""Piper 음성 합성 라이브러리. 명령행 처리나 출력은 호출자가 맡는다."""
from __future__ import annotations

import subprocess
import wave
from pathlib import Path
from typing import Any

DEFAULT_VOICE = "de_DE-thorsten-high"


def ensure_voice(voices_dir: Path, name: str = DEFAULT_VOICE) -> Path:
    """음성 모델을 준비하고 onnx 경로를 돌려준다."""
    onnx = voices_dir / f"{name}.onnx"
    config = voices_dir / f"{name}.onnx.json"
    if not onnx.exists() or not config.exists():
        from piper.download_voices import download_voice

        voices_dir.mkdir(parents=True, exist_ok=True)
        download_voice(name, voices_dir)
    return onnx


def prepare_voice(
    voices_dir: Path,
    name: str = DEFAULT_VOICE,
    *,
    include_alignments: bool = False,
) -> Any:
    """필요하면 모델을 받은 뒤 한 번 로드한다."""
    from piper import PiperVoice

    return PiperVoice.load(ensure_voice(voices_dir, name), include_alignments=include_alignments)


def synthesize(
    voice: Any,
    text: str,
    length_scale: float = 1.0,
    *,
    want_alignments: bool = False,
) -> tuple[bytes, list[dict] | None]:
    """텍스트를 한 속도로 읽어 16비트 PCM과 선택적인 음소 정렬을 돌려준다."""
    from piper import SynthesisConfig

    config = SynthesisConfig(length_scale=length_scale)
    chunks = list(voice.synthesize(text, syn_config=config, include_alignments=want_alignments))
    pcm = b"".join(chunk.audio_int16_bytes for chunk in chunks)

    alignments = None
    if want_alignments:
        alignments, cursor = [], 0.0
        rate = voice.config.sample_rate
        for chunk in chunks:
            for alignment in chunk.phoneme_alignments or []:
                seconds = alignment.num_samples / rate
                alignments.append(
                    {
                        "phoneme": alignment.phoneme,
                        "start": round(cursor, 4),
                        "duration": round(seconds, 4),
                    }
                )
                cursor += seconds
    return pcm, alignments


def write_wav(path: Path, pcm: bytes, sample_rate: int) -> None:
    with wave.open(str(path), "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(sample_rate)
        output.writeframes(pcm)


def to_mp3(wav_path: Path, mp3_path: Path, bitrate: str = "32k") -> None:
    subprocess.run(
        [
            "ffmpeg", "-loglevel", "error", "-y", "-i", str(wav_path),
            "-codec:a", "libmp3lame", "-b:a", bitrate, "-ac", "1", str(mp3_path),
        ],
        check=True,
    )
