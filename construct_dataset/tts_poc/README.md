# tts_poc

독일어 단어 발음 오디오를 이 노트북에서 만든다. 클라우드도, API 키도, 결제
계정도 쓰지 않는다. 네트워크는 음성 모델을 처음 받을 때 한 번만 필요하다.

## 무엇을 만드나

단어 하나에 오디오 파일 하나. 그 안에서 같은 단어를 두 번 읽는다.

```
[보통 속도] ── 0.5초 무음 ── [느린 속도]
```

초보자가 첫 재생으로 전체 인상을 잡고, 두 번째 재생에서 움라우트나 ch처럼
한국어에 없는 소리를 뜯어 듣게 하려는 구성이다. 속도와 간격은 인자로 바꾼다.

## 설치

```bash
./setup.sh
```

가상환경을 만들고 piper-tts를 설치한 뒤 독일어 음성 모델을 받는다. 모델은
109 MB이고 `voices/`에 들어간다. mp3로 저장하려면 ffmpeg이 있어야 한다.
없으면 자동으로 wav로 떨어진다.

## 사용

```bash
# 단어를 직접 넘긴다. 관사를 붙여도 된다.
.venv/bin/python synth.py Vater "das Mädchen" Frühstück

# 파일에서 읽는다. 한 줄에 한 단어.
.venv/bin/python synth.py --file sample_words.txt

# 음소별 타임스탬프를 함께 저장한다.
.venv/bin/python synth.py Vater --alignments
```

결과는 `out/`에 쌓인다. 파일명은 ASCII로 바뀌어 `das Mädchen`은
`das_maedchen.mp3`가 된다. 이미 있는 파일은 건너뛰므로, 단어를 추가한 뒤
다시 돌려도 새 것만 만든다. 전부 다시 만들려면 `--force`를 준다.

## 자주 쓰는 인자

| 인자 | 하는 일 | 기본값 |
|---|---|---|
| `--slow` | 느린 재생의 배속 계수. 클수록 느리다 | `1.45` |
| `--gap` | 두 재생 사이 무음 길이(초) | `0.5` |
| `--once` | 느린 재생 없이 한 번만 읽는다 | 꺼짐 |
| `--voice` | 음성 모델 이름 | `de_DE-thorsten-high` |
| `--format` | `mp3` 또는 `wav` | `mp3` |
| `--alignments` | 음소 타임스탬프를 `.json`으로 저장 | 꺼짐 |
| `--force` | 이미 있는 파일도 다시 만든다 | 꺼짐 |

## 음소 타임스탬프

`--alignments`를 주면 오디오 옆에 같은 이름의 JSON이 생긴다.

```json
{
  "word": "Vater",
  "alignments": [
    { "phoneme": "^", "start": 0.0, "duration": 0.0232 },
    { "phoneme": "f", "start": 0.0232, "duration": 0.0348 },
    { "phoneme": "ˈ", "start": 0.058, "duration": 0.0348 },
    { "phoneme": "ɑ", "start": 0.0929, "duration": 0.0464 }
  ]
}
```

발음 기호를 소리에 맞춰 한 기호씩 밝히는 화면을 만들 수 있다. 쓰기 전에
알아 둘 것이 셋 있다.

첫째, `^`와 `$`는 소리가 아니라 단어의 시작과 끝 표시다.

둘째, 여기 적힌 기호는 합성기 내부의 espeak-ng 표기라 사전 표기와 다르다.
espeak은 Vater를 `fˈɑːtɜ`로 적고 사전은 `ˈfaːtɐ`로 적는다. 소리 자체는
정상이지만, 화면에 보여줄 발음 기호는 위키낱말사전에서 따로 가져오고 두
표기를 잇는 매핑 표를 두어야 한다.

셋째, 결합 문자가 분리되어 나온다. ich의 ç는 `c`와 결합용 세디유 두 항목으로
쪼개진다. 화면에 붙일 때는 결합 문자를 앞 항목에 합쳐야 한 기호로 보인다.

## 다른 목소리

고품질 독일어 음성은 Thorsten 하나뿐이고 남성이다. 다른 선택지는 품질
등급이 낮다.

| 이름 | 품질 |
|---|---|
| `de_DE-thorsten-high` | high |
| `de_DE-thorsten-medium` | medium |
| `de_DE-thorsten_emotional-medium` | medium, 감정 8종 |
| `de_DE-mls-medium` | medium, 236화자 |
| `de_DE-eva_k-x_low` | x_low |

바꾸려면 `--voice de_DE-thorsten_emotional-medium`처럼 넘긴다. 처음 쓰는
모델은 자동으로 받는다.

## 커밋하지 않는 것

`.venv/`, `voices/`, `out/`은 `.gitignore`에 있다. 셋 다 명령 한 줄로
다시 만들어지므로 저장소에 넣을 이유가 없다.
