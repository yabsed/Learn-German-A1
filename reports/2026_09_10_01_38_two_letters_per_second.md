# 모델을 바꾸기 전에 자를 댔다

## 예문이 어색해서 GPU를 꺼내려 했다. 재어 보니 절반은 모델이 아니라 초당 두 글자였다. 이 목소리에 진짜 원본이 있다는 사실이 그것을 증명해 주었다

2026년 9월 10일 | 8 min read

앱이 돌기 시작하자 곧바로 불만이 나왔다. 단어는 그런대로 들을 만한데 예문이
어색하다는 것이다. 노트북에는 RTX 3050이 한 장 있고 그것은 지금까지 아무 일도
하지 않았다. GPU를 쓰는 요즘 음성 합성 모델을 붙이면 되지 않겠느냐는 제안은
자연스러웠다. 실제로 그런 모델은 여럿 있고, 그중 몇은 이 6 GB 카드에 들어간다.

그러나 무엇이 나쁜지 모른 채 도구부터 바꾸는 것은 순서가 아니다. 예문 오디오가
어색하다는 말에는 최소한 세 가지가 섞여 있다. 소리가 잘렸을 수도 있고, 억양이
평평할 수도 있고, 그냥 너무 빠를 수도 있다. 셋은 원인이 다르고 해법도 다르다.
그래서 먼저 쟀다.

## 초당 18.9자

A1 예문 40개를 무작위로 뽑아 길이와 글자 수를 견주었다. 잘린 것은 없었다.
글자당 0.0451초에서 0.0691초 사이에 고르게 들어왔고, 중앙값은 0.0530초였다.
뒤집으면 **초당 18.9자**다.

이 숫자가 큰지 작은지는 그 자체로는 알 수 없다. 비교할 것이 필요했다.

그리고 이 프로젝트에는 운 좋게도 완벽한 비교 대상이 있었다. 지금 쓰는 Piper
음성 모델의 이름은 `de_DE-thorsten-high`다. Thorsten Müller라는 실존 인물이
자기 목소리를 CC0로 공개한 데이터셋으로 학습된 모델이다. 즉 이 합성 음성에는
**같은 사람의 진짜 녹음이 존재한다.** 흔치 않은 조건이다. 보통은 합성 음성을
무엇과 견주어야 할지가 먼저 문제가 되는데, 여기서는 원본이 있다.

그 데이터셋에서 문장 하나를 꺼냈다. 7.11초, 116자.

> Im November vor zwei Jahren habe ich einen Beitrag im Mozilla Forum
> veröffentlicht und meine Stimmspende angekündigt.

같은 문장을 Piper에게 지금 설정 그대로 읽히고 나란히 놓았다.

| | 길이 | 초당 글자 |
|---|---|---|
| Thorsten 본인의 녹음 | 7.11초 | 16.3 |
| Piper, `length_scale=1.0` | 6.40초 | 18.1 |

11퍼센트 빠르다. 숫자로는 작아 보이지만 학습자에게는 그렇지 않다. 독일어를
막 시작한 사람이 듣기에 이 차이는 "따라 읽을 수 있는 속도"와 "한 번 더
들어야 하는 속도"를 가른다. 게다가 이 화자 본인의 데이터셋 전체를 훑어보면
그의 평소 발화는 초당 10자에서 17자 사이에 퍼져 있다. 모델은 그 화자가
실제로 내는 속도보다 꾸준히 빠르게 읽고 있었던 것이다.

## 다섯 개를 만들어 들었다

`length_scale`은 Piper에서 길이 계수다. 1.0보다 크면 느려진다. 같은 문장을
다섯 속도로 만들어 진짜 녹음과 함께 들었다.

| length_scale | 길이 | 초당 글자 | |
|---|---|---|---|
| — | 7.11초 | 16.3 | Thorsten 본인 |
| 1.00 | 6.40초 | 18.1 | 그동안 쓰던 값 |
| 1.15 | 6.75초 | 17.2 | |
| **1.25** | **7.52초** | **15.4** | **골랐다** |
| 1.40 | 7.96초 | 14.6 | |
| 1.60 | 9.15초 | 12.7 | |

1.25가 낫다는 판단이 나왔다. 숫자로 보면 이 값은 진짜 화자보다 아주 조금 느린
자리다. 학습용으로는 그쪽이 옳다. 원어민이 자기 속도로 읽는 것을 그대로 흉내
낼 이유가 없다. 목표는 자연스러움이 아니라 따라 읽을 수 있음이다.

여기서 중요한 것은 결론보다 방법이다. 귀로만 판단했다면 "좀 느리게 해 보자"에서
멈췄을 것이고, 얼마나 느리게가 남았을 것이다. 원본이 있었기 때문에 목표 지점이
숫자로 정해졌다.

## 그래서 GPU는 필요 없나

아니다. 다만 순서가 뒤였다.

속도를 고쳐도 남는 것이 있다. 억양이다. Piper는 CPU에서 돌도록 만든 작은
VITS이고, 문장 안에서 어디를 올리고 어디를 내릴지에 대해 아는 것이 많지 않다.
1.25로 늦춘 것은 또박또박해진 것이지 표현이 생긴 것은 아니다. 그것을 고치려면
모델을 바꿔야 한다.

조사한 것을 남겨 둔다. 6 GB 카드에 들어가면서 독일어를 하는 것들이다.

| 모델 | 독일어 | VRAM | 라이선스 | 판단 |
|---|---|---|---|---|
| F5-TTS German (hvoss-techfak) | Common Voice 19.0으로 420만 step 파인튜닝 | 약 2 GB | CC-BY-NC-4.0 | 1순위 |
| Chatterbox Multilingual | 23개 언어 중 하나 | 8 GB 권장 | MIT | 6 GB에 빠듯 |
| XTTS-v2 | 검증됨 | 약 2 GB | 비상업 | 낡음 |
| Kokoro-82M | **없음** | — | — | 탈락 |

마지막 줄이 이 표에서 가장 쓸모 있는 정보다. Kokoro는 작고 빠르고 라이선스가
깨끗해서 어디서나 첫 번째로 추천되는 모델인데, 공식 `VOICES.md`를 열어 보면
지원 언어에 독일어가 없다. 미국·영국 영어, 일본어, 중국어, 스페인어, 프랑스어,
힌디어, 이탈리아어, 브라질 포르투갈어까지다. 블로그 몇 곳이 독일어를 지원한다고
적어 두었지만 사실이 아니다.

F5-TTS는 설치까지 갔다. `torch 2.14.0+cu130`이 RTX 3050을 정상적으로 잡았고
가상환경은 6.3 GB다. 체크포인트 1.35 GB만 다시 받으면 바로 돌릴 수 있는 상태로
`construct_dataset/f5_poc/`에 남아 있다. 다만 그 길에는 대가가 따른다. Piper는
VITS라 헛소리를 하지 않지만, F5는 흐름 정합 모델이라 가끔 한다. 모델
토론방에 "출력이 그냥 횡설수설"이라는 제목의 글이 실제로 있다. 9,422개를 무인으로
돌린 뒤 학습자가 잘못된 발음을 외우는 것은 억양이 평평한 것보다 훨씬 나쁘므로,
그쪽으로 간다면 생성한 음성을 다시 받아쓰기해 원문과 대조하는 8단계가 함께
와야 한다. 그것은 오늘 할 일이 아니다.

## 단어까지 바꾼 이유

고칠 곳은 `06_audio.py` 한 군데다. 그런데 예문만 늦추면 문제가 생긴다.

이 앱에서 단어는 보통 속도로 한 번, 0.5초 쉬고 느린 속도로 한 번 더 읽는다.
예문은 한 번만 읽는다. 예문만 1.25로 옮기면 같은 목소리가 단어는 초당 18자로,
문장은 15자로 읽게 된다. 카드를 넘길 때마다 화자가 서둘렀다 늦췄다 하는 셈이다.
이 프로젝트가 원어민 녹음을 버리고 합성으로 간 이유가 바로 그 균일함이었다.

그래서 보통 속도를 손잡이 하나로 모았다. 단어의 첫 읽기와 예문이 같은 값을
쓴다. 단어의 두 번째 읽기는 원래 첫 읽기의 1.45배였으므로 그 비율을 지켜
1.8로 옮겼다. 움라우트와 ch가 두 번째 재생에서 또렷하게 갈라지는 것이 그 패스의
목적이고, 1.25 옆에 1.45를 두면 그 대비가 거의 사라진다.

`work_items`가 바뀐 자리가 그것이다. 전에는 "두 번 읽을지"를 참·거짓으로
넘겼다.

```python
yield item_id, word["lemma"], True       # 단어
yield item_id, sentence["de"], False     # 예문
```

지금은 읽을 속도를 그대로 넘긴다.

```python
yield item_id, word["lemma"], (scale, slow)   # 단어: 보통, 느리게
yield item_id, sentence["de"], (scale,)       # 예문: 보통 한 번
```

참·거짓이 값으로 바뀌자 합성 쪽 분기가 사라졌다.

```python
# 전
pcm, _ = synthesize(voice, text)
if twice:
    slow, _ = synthesize(voice, text, args.slow)
    pcm = pcm + silence + slow

# 후
pcm = silence.join(synthesize(voice, text, scale)[0] for scale in scales)
```

속도가 하나면 무음이 낄 자리가 없고 둘이면 사이에 낀다. `join`이 그 규칙을
이미 알고 있으므로 따로 적을 것이 없다.

같이 들어간 것이 `--only`다. 예문 속도만 다시 손보고 싶을 때 단어 3,005개를
다시 만들 이유가 없다.

```bash
python scripts/06_audio.py --levels a1 --only sentences --force
```

## 지운 것과 다시 만드는 것

기존 mp3 3,892개를 모두 지웠다. A1 전체와 A2 단어, B1 단어 21개가 들어 있었다.
겁나는 작업처럼 보이지만 그렇지 않다. 이 파일들은 전부 git에 커밋되어 있고
워킹 트리는 깨끗했다. 되돌리려면 한 줄이면 된다.

```bash
git checkout -- construct_dataset/data/audio
```

지우고 다시 만드는 쪽을 고른 것은 속도 설정이 파일 이름이나 내용 어디에도 남지
않기 때문이다. 어떤 mp3가 옛 속도이고 어떤 것이 새 속도인지 나중에 구별할 방법이
없다. 절반만 바뀐 데이터셋보다 다 지우고 다시 만든 데이터셋이 낫다.

한 가지 더 고쳤다. `07_site.py`가 앱 폴더로 오디오를 하드링크할 때 이미 있는
파일을 건너뛸지 판단하는 기준이 파일 크기였다.

```python
if target.stat().st_size == source.stat().st_size:   # 전
if target.stat().st_ino == source.stat().st_ino:     # 후
```

같은 크기라고 같은 파일은 아니다. 다시 만든 mp3가 우연히 옛것과 같은 바이트 수가
되면 앱에는 옛 소리가 그대로 남는다. inode를 견주면 그런 일이 없다. 하드링크가
같은 파일을 가리키는지 묻는 데 크기를 쓸 이유가 애초에 없었다.

## 그래서 다음은

지금 상태에서 앱은 완결되어 있다. 남은 것은 둘이다.

A2와 B1의 예문 오디오 3,832개가 아직 없다. 새 속도로 만들면 되고, 이제
`--levels a2,b1` 한 줄이다.

그다음이 모델이다. 속도를 고친 소리를 며칠 써 보고도 억양이 걸리면 그때
`f5_poc/`를 다시 꺼내면 된다. 환경은 이미 깔려 있고 체크포인트 하나만 받으면
된다. 걸리지 않으면 6.3 GB를 지우면 된다. 어느 쪽이든, 오늘 잰 숫자가 없었다면
그 판단을 할 수 없었을 것이다. ■

<details>
<summary>바뀐 코드 전체와 디렉터리 구조 펼쳐 보기</summary>

### 바뀐 파일

| 파일 | 바뀐 것 |
|---|---|
| `scripts/06_audio.py` | `--scale` 신설, `--slow` 기본값 1.45 → 1.8, `--only` 신설, `work_items`가 속도를 넘김 |
| `scripts/07_site.py` | 하드링크 판정을 크기에서 inode로 |
| `tests/test_pipeline.py` | `work_items` 반환 형태와 `--only` 검사 |

### scripts/06_audio.py 의 핵심

```python
def work_items(words: list[dict], sentences: list[dict], levels: set[str],
               scale: float = 1.25, slow: float = 1.8, only: str = "all"):
    """(데이터셋 id, 읽을 텍스트, 읽을 속도들) 을 만든다.

    속도가 둘이면 그 둘을 무음으로 이어 붙인다. 단어는 보통 속도로 한 번,
    느린 속도로 한 번 더. 예문은 보통 속도로 한 번만.
    """
    seen: set[str] = set()
    if only in ("all", "words"):
        for word in words:
            if word["level"].lower() in levels:
                item_id = word["id"]
                if item_id in seen:
                    raise ValueError(f"duplicate audio id: {item_id}")
                seen.add(item_id)
                yield item_id, word["lemma"], (scale, slow)
    if only in ("all", "sentences"):
        for sentence in sentences:
            if sentence["level"].lower() in levels:
                item_id = sentence["id"]
                if item_id in seen:
                    raise ValueError(f"duplicate audio id: {item_id}")
                seen.add(item_id)
                yield item_id, sentence["de"], (scale,)
```

합성 반복문은 이렇게 짧아졌다. 임시 wav 를 거쳐 mp3 로 인코딩하고, 다 되면
제자리에 옮긴다. 중간에 끊겨도 반쯤 쓰인 mp3 가 남지 않는다.

```python
for index, (item_id, text, scales) in enumerate(pending, 1):
    pcm = silence.join(synthesize(voice, text, scale)[0] for scale in scales)
    wav = args.out / f".{item_id}.wav"
    encoded = args.out / f".{item_id}.mp3"
    final = args.out / f"{item_id}.mp3"
    try:
        write_wav(wav, pcm, rate)
        to_mp3(wav, encoded, args.bitrate)
        encoded.replace(final)
    finally:
        wav.unlink(missing_ok=True)
        encoded.unlink(missing_ok=True)
```

### 속도를 재는 데 쓴 코드

```python
import json, subprocess, random, statistics
S = json.load(open('data/sentences.json'))
a1 = [s for s in S if s['level'] == 'A1']
random.seed(7); pick = random.sample(a1, 40)
rows = []
for s in pick:
    out = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
                          '-of', 'csv=p=0', f'data/audio/{s["id"]}.mp3'],
                         capture_output=True, text=True)
    d = float(out.stdout.strip())
    rows.append((d, len(s['de']), d / max(1, len(s['de'])), s['de']))
rate = [r[2] for r in rows]
print(f"글자당 초: 중앙값 {statistics.median(rate):.4f}  최소 {min(rate):.4f}  최대 {max(rate):.4f}")
```

Thorsten 본인의 녹음은 데이터셋 396 MB 를 받지 않고 행 단위 API 로 한 클립만
꺼냈다. `charsPerSecond` 가 데이터셋에 이미 들어 있어서 그의 평소 발화 속도를
따로 계산할 필요도 없었다.

```python
import json, urllib.request
base = ("https://datasets-server.huggingface.co/rows"
        "?dataset=Thorsten-Voice/TV-24kHz-Neutral&config=default&split=train")
with urllib.request.urlopen(f"{base}&offset=0&length=100") as r:
    for it in json.load(r)['rows']:
        w = it['row']
        print(w['durationSeconds'], w['charsPerSecond'], w['text'])
```

### 지금 구조

```text
learn-german-voca/
├── Makefile                       site · serve · data
├── construct_dataset/
│   ├── scripts/
│   │   ├── 01_wordlist.py … 05_merge.py
│   │   ├── 06_audio.py            ← --scale 1.25, --slow 1.8, --only
│   │   ├── 07_site.py             ← inode 로 하드링크 판정
│   │   └── piper_tts.py
│   ├── data/audio/                다 지우고 다시 만드는 중
│   ├── tts_poc/
│   │   ├── voices/                Piper 모델 109 MB
│   │   └── out/speed/             이 보고서의 비교 음원 11개
│   └── f5_poc/                    GPU 쪽 실험. 환경만 깔려 있다
│       ├── .venv/                 6.3 GB, torch 2.14.0+cu130
│       ├── model/                 비어 있음. 체크포인트 1.35 GB 를 받아야 한다
│       └── ref/                   비어 있음
└── app/                           make site 가 채운다
```

### 들어 본 음원

`construct_dataset/tts_poc/out/speed/` 에 남겼다. 앱 데이터가 아니라 판단의
근거다.

| 파일 | 내용 |
|---|---|
| `00_real_thorsten.mp3` | Thorsten 본인의 녹음 (CC0) |
| `piper_1_0.mp3` … `piper_1_6.mp3` | 같은 문장, 다섯 속도 |
| `Vater_word_now_1.0+1.45.mp3` 외 | 단어 두 패스, 옛 조합과 새 조합 |

</details>

---

출처
- [Thorsten-Voice/TV-24kHz-Neutral, CC0 독일어 음성 데이터셋](https://huggingface.co/datasets/Thorsten-Voice/TV-24kHz-Neutral)
- [hvoss-techfak/F5-TTS-German](https://huggingface.co/hvoss-techfak/F5-TTS-German)
- [F5-TTS 독일어 모델 토론, "Output just gibberish"](https://huggingface.co/marduk-ra/F5-TTS-German/discussions/9)
- [Kokoro-82M VOICES.md, 지원 언어 목록](https://huggingface.co/hexgrad/Kokoro-82M/blob/main/VOICES.md)
- [resemble-ai/chatterbox](https://github.com/resemble-ai/chatterbox)
