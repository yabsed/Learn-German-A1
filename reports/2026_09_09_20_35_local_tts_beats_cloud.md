# 클라우드는 필요 없었다

## 독일어 발음 오디오를 만드는 데 결제 계정이 필요하다고 적었다. 노트북에서 돌려 보니 7분이면 끝나는 일이었다

2026년 9월 9일 오후 8시 35분 | 9 min read

몇 분 전 같은 자리에서 쓴 보고서는 오디오를 클라우드 음성 합성으로 만들라고 권했다. Google Cloud Text-to-Speech에 단어를 넣고 mp3를 받아 두라는 것이었다. 근거는 통제력이었다. SSML이라는 마크업으로 말 속도와 쉼을 지시할 수 있으니, 보통 속도로 한 번 읽고 느리게 한 번 더 읽는 구성을 만들 수 있다는 이야기였다. 요금은 무료 할당량 안에 들어가니 걱정할 것 없다고도 적었다.

그 권고에는 확인하지 않은 전제가 하나 깔려 있었다. 노트북에서는 이만한 품질이 안 나온다는 전제다. 몇 년 전이라면 맞는 말이었다. 지금은 아니다.

## 11초와 7분

확인은 간단했다. 이 노트북은 라이젠 7 8845HS에 스레드 16개를 갖고 있고, 램은 13 GB다. RTX 3050도 달려 있지만 결국 쓰지 않았다. Piper라는 오프라인 음성 합성기를 가상환경에 설치하고, 독일어 음성 모델을 받아, 단어 18개를 두 속도씩 합성하는 데까지 걸린 시간을 재 봤다.

| 항목 | 측정값 |
|---|---|
| 설치와 모델 다운로드 전체 | 11초 |
| 음성 모델 크기 | 109 MB |
| 모델 로드 | 0.8초 |
| 단어당 합성 (두 속도 합쳐) | 0.35초 |
| 1,300단어 전체 환산 | 약 7.5분 |
| 완성 mp3 하나 | 평균 17 KB |
| 오디오 전체 | 약 22 MB |

CPU만 쓴 수치다. 클라우드에 요청을 1,300번 보내고 응답을 기다리는 것보다 빠를 가능성이 높다.

품질은 Thorsten이라는 음성이 담당한다. 토르스텐 뮐러라는 독일인이 몇 해에 걸쳐 자기 목소리를 녹음해 공개 도메인으로 풀어 놓은 데이터로 훈련된 모델이다. Piper가 제공하는 171개 음성 중 최고 등급으로 훈련된 것은 13개뿐이고, 독일어로는 이것 하나다.

## 요금이 문제가 아니었다

설치가 빠르다는 사실은 흥미롭지만 결정적이지는 않다. 판단을 뒤집은 것은 그다음이다.

SSML이 필요 없어진다. 앞선 보고서는 단어 하나마다 이런 마크업을 만들어 보내라고 했다.

```xml
<speak>
  <prosody rate="100%">Vater</prosody>
  <break time="500ms"/>
  <prosody rate="70%">Vater</prosody>
</speak>
```

Piper에는 `length_scale`이라는 값이 있다. 1.0이 기본이고 키우면 느려진다. 마크업을 문자열로 조립해 원격 서비스에 보내고 그쪽 파서가 해석해 주기를 기다리는 대신, 숫자 하나를 함수에 넘긴다. 무음도 마크업으로 부탁할 필요가 없다. 16비트 정수 배열에 0을 원하는 만큼 채우면 그게 무음이다. 실제 코드에서 두 속도를 잇는 부분은 이렇게 짧아졌다.

```python
pcm, alignments = synthesize(voice, word, 1.0, args.alignments)
if not args.once:
    slow, _ = synthesize(voice, word, args.slow, False)
    pcm = pcm + silence + slow
```

첫 줄이 보통 속도, 셋째 줄이 느린 속도, 넷째 줄이 둘을 무음으로 잇는 부분이다. 그 `silence`는 앞에서 한 줄로 만들어 둔다. `b"\x00\x00" * int(rate * args.gap)`이 전부다.

그리고 몇 번이든 다시 만들 수 있다는 점이 생각보다 크다. 느린 쪽이 과하게 늘어져 들리면 계수를 1.45에서 1.3으로 바꾸고 다시 돌리면 된다. 7분이다. 클라우드였다면 매번 할당량을 세면서 망설였을 일이고, 망설이는 순간 "이 정도면 됐다"에서 멈추게 된다. 학습 도구의 품질은 그 멈추는 지점에서 결정된다.

셋업 마찰도 사라진다. 프로젝트를 만들고 결제 계정을 연결하고 서비스 계정 키를 받아 환경 변수에 꽂는 과정이, 스크립트 하나를 실행하는 일로 줄어든다. 앞선 보고서는 이 프로젝트에서 사람이 할 일은 한국어 뜻을 검수하는 30분뿐이라고 했다. 클라우드 설정에 드는 시간을 계산에 넣지 않은 값이었다.

## 예상하지 못한 소득

Piper는 요청하면 음소별 타임스탬프를 함께 내준다. 단어를 합성하면 어떤 소리가 몇 초에 시작해 얼마나 지속되는지가 배열로 딸려 온다. ich를 넣으면 이런 결과가 나온다.

```json
{
  "word": "ich",
  "alignments": [
    { "phoneme": "^", "start": 0.0,    "duration": 0.0929 },
    { "phoneme": "ɪ", "start": 0.0929, "duration": 0.0464 },
    { "phoneme": "c", "start": 0.1393, "duration": 0.1161 },
    { "phoneme": "̧",  "start": 0.2554, "duration": 0.058  },
    { "phoneme": "$", "start": 0.3135, "duration": 0.058  }
  ]
}
```

이것이 왜 중요한지는 애초의 목적을 떠올리면 분명해진다. 파닉스를 막 뗀 학습자가 알고 싶은 것은 "이 단어가 이렇게 들린다"가 아니라 "이 글자가 이 소리를 낸다"이다. 타임스탬프가 있으면 오디오가 흐르는 동안 발음 기호를 한 기호씩 밝힐 수 있다. ich의 ch가 소리 나는 그 0.116초 동안 화면의 ç가 켜진다. 클라우드 음성 합성으로는 이 정보를 얻기 어렵다.

다만 그대로 쓸 수는 없다. 위 JSON에서 `^`와 `$`는 소리가 아니라 단어의 시작과 끝 표시다. ç가 `c`와 결합용 세디유 두 항목으로 쪼개져 나오는 것도 보인다. 화면에 붙이려면 결합 문자를 앞 항목에 합치는 처리가 필요하다.

## 대신 감수할 것

첫째, 목소리 선택지가 좁다. 고품질 독일어 음성은 Thorsten 하나이고 남성이다. 여성 음성인 eva_k와 kerstin과 ramona는 품질 등급이 낮다. Thorsten에는 감정 8종이 담긴 중간 품질 버전이 따로 있어, 더 또렷하고 강한 톤을 원한다면 그쪽을 시험해 볼 만하다.

둘째, 자연스러움은 클라우드 쪽이 아직 조금 앞선다. 다만 그 격차는 긴 문장의 억양에서 벌어진다. 이 앱이 다루는 것은 단어 하나짜리 발화이고, 거기서는 차이가 거의 드러나지 않는다.

셋째가 실질적으로 가장 성가시다. Piper는 espeak-ng을 내부 음소 변환기로 쓰는데, espeak의 기호 표기가 사전과 다르다.

| 단어 | espeak 표기 | 사전 표기 |
|---|---|---|
| Vater | `fˈɑːtɜ` | `ˈfaːtɐ` |
| Väter | `fˈɛːtɜ` | `ˈfɛːtɐ` |
| Straße | `ʃtɾˈɑːsə` | `ˈʃtʁaːsə` |

소리 자체는 정상이다. Thorsten 모델은 독일인의 실제 발화로 훈련되었고, espeak의 기호는 그 모델에 들어가는 내부 라벨일 뿐이다. 문제는 이 라벨을 화면에 그대로 보여줄 수 없다는 것이다. 따라서 앞선 보고서의 결론 하나는 그대로 살아남는다. 학습자에게 보여줄 발음 기호는 위키낱말사전에서 가져와야 한다. 여기에 더해, 타임스탬프 기능을 붙이려면 두 표기를 잇는 매핑 표를 만들어야 한다는 숙제가 생겼다.

## 만들어 둔 것

주장만 남기는 대신 돌아가는 코드를 함께 두었다. `construct_dataset/tts_poc/`에 임의의 독일어 단어를 오디오로 바꾸는 도구가 있고, 위의 모든 수치는 이 도구를 실제로 돌려 얻은 것이다.

```bash
./setup.sh                                              # 한 번만. 11초 걸린다
.venv/bin/python synth.py Vater "das Mädchen"           # 단어를 직접 넘긴다
.venv/bin/python synth.py --file sample_words.txt       # 파일에서 읽는다
```

결과는 `out/`에 쌓이고, 파일명은 ASCII로 바뀐다. `das Mädchen`은 `das_maedchen.mp3`가 된다. 움라우트가 든 파일명은 웹 서버와 압축 도구마다 다루는 방식이 달라 사고가 나기 쉬워서다. 이미 만든 파일은 건너뛰므로 단어를 추가한 뒤 다시 돌려도 새 것만 만든다.

목록에 없는 단어도 당연히 된다. Geschwindigkeitsbegrenzung처럼 26글자짜리 합성어를 넣어도 0.5초면 나온다.

<details>
<summary>디렉토리 구조와 합성 코드 전문 펼쳐 보기</summary>

```
construct_dataset/tts_poc/
├── README.md              # 사용법과 주의사항
├── setup.sh               # 가상환경 생성 + 설치 + 모델 다운로드
├── requirements.txt       # piper-tts[alignment]
├── synth.py               # 본체
├── sample_words.txt       # 시연용 단어 18개
├── .gitignore             # 아래 셋을 제외한다
├── .venv/                 # 가상환경 (196 MB)
├── voices/                # 음성 모델 (109 MB)
└── out/                   # 생성된 mp3와 타임스탬프 JSON
```

`.venv`와 `voices`와 `out`은 저장소에 넣지 않는다. 셋 다 명령 한 줄로 다시 만들어진다.

합성의 핵심은 이 함수다. 한 속도로 한 번 읽어 PCM 바이트열과 음소 정렬을 돌려준다.

```python
def synthesize(voice: PiperVoice, text: str, length_scale: float, want_alignments: bool):
    """단어 하나를 한 속도로 읽어 16비트 PCM 바이트열과 음소 정렬을 돌려준다."""
    cfg = SynthesisConfig(length_scale=length_scale)
    chunks = list(voice.synthesize(text, syn_config=cfg,
                                   include_alignments=want_alignments))
    pcm = b"".join(c.audio_int16_bytes for c in chunks)

    alignments = None
    if want_alignments:
        alignments, cursor = [], 0.0
        rate = voice.config.sample_rate
        for chunk in chunks:
            for a in (chunk.phoneme_alignments or []):
                seconds = a.num_samples / rate
                alignments.append(
                    {"phoneme": a.phoneme,
                     "start": round(cursor, 4),
                     "duration": round(seconds, 4)}
                )
                cursor += seconds
    return pcm, alignments
```

파일명 변환은 이렇게 한다. 움라우트를 두 글자로 풀고 나머지는 밑줄로 만든다.

```python
TRANSLITERATE = str.maketrans(
    {"ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss", "Ä": "ae", "Ö": "oe", "Ü": "ue"}
)

def slugify(word: str) -> str:
    """'das Mädchen' -> 'das_maedchen'."""
    s = word.translate(TRANSLITERATE).lower()
    s = re.sub(r"[^a-z0-9]+", "_", s).strip("_")
    return s or "word"
```

음성 모델은 없으면 알아서 받는다. 그래서 `setup.sh`가 하는 일이라고는 가상환경을 만들고 `--download-only`로 한 번 호출하는 것뿐이다.

```python
def ensure_voice(voices_dir: Path, name: str) -> Path:
    """음성 모델이 없으면 받는다. 있으면 그대로 쓴다."""
    onnx = voices_dir / f"{name}.onnx"
    if not onnx.exists():
        voices_dir.mkdir(parents=True, exist_ok=True)
        print(f"음성 모델 내려받는 중: {name}", file=sys.stderr)
        download_voice(name, voices_dir)
    return onnx
```

인자로 조절할 수 있는 것들이다.

| 인자 | 하는 일 | 기본값 |
|---|---|---|
| `--slow` | 느린 재생의 배속 계수 | `1.45` |
| `--gap` | 두 재생 사이 무음 초 | `0.5` |
| `--once` | 느린 재생 없이 한 번만 | 꺼짐 |
| `--voice` | 음성 모델 이름 | `de_DE-thorsten-high` |
| `--alignments` | 타임스탬프를 JSON으로 저장 | 꺼짐 |
| `--force` | 이미 있는 파일도 다시 만든다 | 꺼짐 |

`--slow`와 `--gap`을 바꾸면 오디오 길이가 실제로 달라지는지도 확인했다.

| 설정 | Vater 오디오 길이 |
|---|---|
| `--once` | 0.63초 |
| 기본값 | 2.03초 |
| `--slow 2.0 --gap 0.8` | 2.33초 |

</details>

## 파이프라인은 어떻게 바뀌나

앞선 보고서가 그린 다섯 단계 중 넷은 그대로다. 괴테 인스티투트 단어 목록을 받고, kaikki.org 추출본에서 발음 기호를 대조해 붙이고, 언어 모델로 한국어 뜻을 채운 뒤 사람이 검수하고, 마지막에 JSON 하나와 mp3 폴더를 정적 페이지에 담아 올린다. 서버가 필요 없다는 결론도 그대로다. 오히려 더 확실해졌다. 이제는 빌드 시점에도 외부 서비스를 부르지 않는다.

바뀐 것은 네 번째 단계다. 클라우드에 요청을 보내던 자리에 노트북에서 도는 스크립트가 들어갔고, 그 스크립트는 이미 작성되어 돌아간다. 남은 것은 앞의 세 단계다. 단어 목록과 발음 기호와 한국어 뜻이 갖춰지는 순간, 오디오는 7분 뒤에 나온다. ■

---

관련 문서
- [2026_09_09_20_28_german_phonics_app.md](2026_09_09_20_28_german_phonics_app.md) - 이 보고서가 수정하는 앞선 권고
- [construct_dataset/tts_poc/](../construct_dataset/tts_poc/) - 여기서 측정한 모든 수치의 출처

출처
- [rhasspy/piper](https://github.com/rhasspy/piper)
- [Thorsten-Voice 데이터셋](https://zenodo.org/records/7265581)
- [rhasspy/piper-voices, 음성 목록](https://huggingface.co/rhasspy/piper-voices)
- [espeak-ng](https://github.com/espeak-ng/espeak-ng)
