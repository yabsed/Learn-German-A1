# 단어장 데이터가 태어나는 곳

## 괴테의 단어 목록에서 출발해 뜻과 발음, 예문 번역과 음성까지 만든다

이 디렉터리에는 학습 앱이 없다. 앱이 먹을 재료를 만드는 공장이 있다.
괴테 인스티투트의 A1·A2·B1 단어 목록을 읽고, 독일어판 위키낱말사전에서
발음 기호를 찾고, 언어 모델로 한국어 뜻과 예문 번역을 쓴다. 마지막에는
Piper가 단어와 문장을 mp3로 읽는다.

텍스트 완성품은 둘이다. `data/words.json`에는 단어 3,005개가,
`data/sentences.json`에는 중복을 걷어낸 예문 6,417개가 들어간다. 소리는 두
파일이 정해 준 id를 그대로 이름 삼아 `data/audio/{id}.mp3`에 놓인다. 텍스트에서
파일명을 다시 만들지 않으므로, 문장부호 하나가 다른 두 문장이 같은 소리를
덮어쓸 일도 없다.

```text
괴테 TSV ──→ 단어 목록 ──→ IPA ──→ 단어 뜻 ──→ 예문 번역 ──→ JSON 두 개
                                                                    │
                                                                    └──→ mp3
```

## 처음부터 끝까지 한 번에 실행하기

시작하기 전에 `git`, `curl`, `uv`, `ffmpeg`가 있어야 한다. 언어 모델은
`ANTHROPIC_API_KEY`나 `ANTHROPIC_AUTH_TOKEN`이 설정되어 있거나, 로컬에서
`claude` 또는 `codex` CLI를 실행할 수 있어야 한다.

조건이 갖춰졌다면 저장소 루트에서 다음 한 줄로 전체 파이프라인을 실행한다.

```bash
make -C construct_dataset setup all audio AUDIO_ARGS="--levels a1,a2,b1"
```

이 명령은 Python 환경과 원본 단어 목록을 준비하고, 텍스트 데이터 전체를 만든
뒤, A1부터 B1까지 모든 오디오를 합성한다. 첫 실행에서는 Kaikki 압축 덤프 약
303MB와 Piper 음성 모델 약 109MB를 받는다. 단어 뜻과 예문 번역은 언어 모델을
호출하므로 사용량과 비용이 생길 수 있고, 오디오까지 끝내려면 시간이 꽤 걸린다.

다시 실행해도 처음부터 되풀이하지는 않는다. 번역이 끝난 id와 이미 존재하는
mp3는 건너뛴다. 긴 작업이 중간에 끊겼다면 같은 명령을 다시 실행하면 된다.

## 이제 한 단계씩 들여다보자

한 줄짜리 명령이 하는 일은 여섯 단계다. 문제를 찾거나 일부 데이터만 고칠
때는 아래 명령을 따로 실행하는 편이 빠르다. 여기서부터는 모두
`construct_dataset/` 안에서 실행한다고 가정한다.

### 0. 실행 환경을 준비한다

```bash
make setup
```

텍스트 파이프라인용 `.venv`를 만들고 Python 의존성을 설치한 뒤, 괴테 단어
목록이 든 git submodule을 가져온다. 오디오 환경은 훨씬 크므로 여기에 섞지
않는다.

### 1. 괴테 TSV를 단어 목록으로 바꾼다

```bash
make wordlist
```

괴테 TSV의 표제어와 예문을 읽어 `data/wordlist.jsonl`을 만든다. 관사와 복수형
힌트, 동사 변화형처럼 한 칸에 섞인 정보를 이 단계에서 분리한다. 단어 id도
여기서 확정된다.

### 2. 발음 기호를 찾는다

```bash
make ipa
```

독일어판 위키낱말사전 추출본에서 각 단어의 IPA를 찾는다. 덤프가 없으면 약
303MB를 먼저 내려받고, 압축을 풀지 않은 채 훑는다. 결과는
`data/ipa.jsonl`에 남는다.

### 3. 단어의 한국어 뜻을 쓴다

```bash
make ko
```

언어 모델이 단어와 예문, 품사 힌트를 읽고 한국어 뜻과 짧은 학습 메모를 쓴다.
결과는 `data/ko_draft.tsv`에 누적된다. A1만 처리하거나 모델과 동시 요청 수를
지정할 수도 있다.

```bash
make ko KO_ARGS="--levels a1 --model sonnet --workers 4"
make ko KO_ARGS="--levels a1 --backend codex --workers 4"
```

### 4. 예문을 한국어로 번역한다

```bash
make sentences
```

6,580개 예문에서 같은 독일어 문장을 합치면 6,417개가 남는다. 언어 모델은 이
문장들만 한 번씩 번역하고 `data/sentence_draft.tsv`에 이어 쓴다. 기본 effort는
`low`다.

```bash
make sentences SENTENCE_ARGS="--levels a1 --model sonnet --workers 4"
make sentences SENTENCE_ARGS="--levels a1 --backend codex --workers 4"
```

3~5단계는 기본값 `auto`에서 API 자격 증명이 있으면 Anthropic SDK를 쓰고,
없으면 `claude` CLI를 찾는다. `--backend codex`를 주면 Codex CLI를 쓴다.
이미 저장된 id는 다시 요청하지 않으므로 중단 후 재실행해도 앞선 비용을
되풀이하지 않는다.

### 5. 예문에 행간 문맥 뜻을 붙인다

```bash
make glosses GLOSS_ARGS="--levels a1 --model sonnet --workers 4"
make glosses GLOSS_ARGS="--levels a1 --backend codex --model gpt-5.6-luna --workers 4 --chunk 20"
```

이미 만든 자연스러운 한국어 번역을 다시 번역하지 않고, 독일어의 연속된
낱말 범위와 그 범위의 짧은 문맥 뜻만 생성한다. 모델 출력은 `[낱말 수, 뜻]`
배열이라 독일어 원문을 되풀이하지 않는다. 결과는 `data/gloss_draft.jsonl`에
id별로 누적된다. `--limit 60 --dry-run`으로 실제 호출 없이 입력을 확인할 수 있다.

### 6. 앱이 읽는 JSON을 만든다

```bash
make merge
```

앞 단계 산출물과 사람이 고친 `data/overrides.tsv`를 합쳐 `data/words.json`과
`data/sentences.json`을 만든다. 발음이나 뜻 하나만 고친 뒤라면 1~4단계를
다시 돌릴 필요 없이 이 명령만 실행하면 된다. 문맥 주석은
`data/gloss_overrides.jsonl`의 같은 id가 자동 초안보다 우선한다. 검토가 필요한
단어와 예문은 `data/review_queue.tsv`, `data/gloss_review_queue.tsv`에 적히고,
등급별 통계는 `data/stats.json`에 적힌다.

### 7. 단어와 문장을 mp3로 읽는다

```bash
make audio
```

별도 환경인 `tts_poc/.venv`와 Piper 음성 모델을 준비하고 A1 오디오를 만든다.
단어는 화면의 관사나 괄호 표현이 아니라 정리된 `lemma`를 보통 속도로 한 번,
0.5초 뒤 느린 속도로 한 번 더 읽는다. 예문은 원문을 보통 속도로 한 번만 읽는다.
결과는 mp3 32k 모노 파일이다.

`length_scale`은 1.0으로 읽히면 초당 18자가 된다. 이 음성 모델의 원본 화자가
같은 문장을 읽은 속도는 16.3자였다. 단어와 예문은 일부러 다른 값을 쓴다.
단어는 1.25(초당 15.4자)로 화자와 비슷하게 두었다. 짧아서 더 늦추면 늘어지고,
어차피 1.8로 한 번 더 읽어 주므로 첫 읽기까지 느릴 이유가 없다. 예문은
1.6(초당 12.7자)으로 화자보다 느리다. 길어서 따라 읽으려면 그만큼 여유가
필요하다. 이 값도 화자 본인의 발화 범위(초당 10~17자) 안에는 든다. 재어 본
과정은 [보고서](../reports/2026_09_10_01_38_two_letters_per_second.md)에 있다.

```bash
make audio AUDIO_ARGS="--levels a1 --word-scale 1.25 --slow 1.8 --sentence-scale 1.6"
```

예문 속도만 다시 손볼 때는 단어 3,005개를 다시 만들 이유가 없다.

```bash
make audio AUDIO_ARGS="--levels a1 --only sentences --force"
```

A2와 B1까지 만들거나 기존 파일을 다시 만들려면 범위를 명시한다.

```bash
make audio AUDIO_ARGS="--levels a1,a2,b1"
make audio AUDIO_ARGS="--levels a1 --force"
```

환경과 모델만 미리 준비하려면 `make setup-audio`를 실행한다.

### 8. 앱이 쓸 자리로 옮긴다

```bash
make site
```

`words.json`과 `sentences.json`은 셋을 합쳐 3 MB 가까이 된다. 앱은 한 번에 한
등급만 쓰므로 등급 하나만 담은 `../app/data/a1.json`을 따로 만들고, 오디오는
복사하지 않고 하드링크로 건다. 같은 파일을 두 번 저장하지 않는다.

```bash
make site SITE_ARGS="--levels a1,a2,b1"
```

앱을 띄우는 것은 저장소 루트의 `make serve`다. 자세한 것은 [`app/README.md`](../app/README.md)에 있다.

## 아무 독일어나 바로 들어볼 수도 있다

데이터셋에 넣지 않고 발음만 확인하고 싶을 때는 전체 파이프라인이 지나치다.
즉석 합성 도구는 그 일을 위해 남아 있다.

```bash
tts_poc/.venv/bin/python tools/say.py Geschwindigkeitsbegrenzung
tts_poc/.venv/bin/python tools/say.py "Auf Wiedersehen!" --once
```

이 도구는 읽기 쉬운 슬러그로 `tts_poc/out/`에 저장한다. 그 이름은 임시
도구 안에서만 살며 앱 데이터와는 아무 관계가 없다.

## 바뀐 것이 의심스럽다면

```bash
.venv/bin/python -m unittest discover -s tests -v
```

테스트는 id 규칙, 예문 중복 제거, 등급별 문장 수, 오디오 id 충돌, 병합된 예문
참조와 LLM 재시도를 확인한다. 현재 기준은 단어 3,005개, 문장 6,417개, 서로
겹치지 않는 오디오 id 9,422개다.

`make clean`은 다시 만들기 싼 중간 산출물과 최종 JSON만 지운다. 돈을 들여
만든 번역 초안, 303MB 원본 덤프와 합성된 오디오는 남긴다.

<details>
<summary>단계별 파일과 디렉터리 구조 펼쳐 보기</summary>

| 단계 | 실행 파일 | 주 입력 | 주 출력 |
|---|---|---|---|
| 1 | `scripts/01_wordlist.py` | 괴테 TSV | `data/wordlist.jsonl` |
| 2 | `scripts/02_ipa.py` | Kaikki 덤프 | `data/ipa.jsonl` |
| 3 | `scripts/03_ko.py` | 단어 목록·IPA | `data/ko_draft.tsv` |
| 4 | `scripts/04_sentences.py` | 단어 목록의 예문 | `data/sentence_draft.tsv` |
| 5 | `scripts/05_glosses.py` | 독일어 예문·한국어 번역 | `data/gloss_draft.jsonl` |
| 6 | `scripts/06_merge.py` | 앞 단계 출력·수동 수정 | `data/words.json`, `data/sentences.json` |
| 7 | `scripts/07_audio.py` | 최종 JSON 두 개 | `data/audio/{id}.mp3` |
| 8 | `scripts/08_site.py` | 최종 JSON·오디오 | `../app/data/{등급}.json`, `../app/audio/` |

```text
construct_dataset/
├── Makefile
├── requirements.txt
├── requirements-audio.txt
├── scripts/
│   ├── common.py
│   ├── ids.py
│   ├── llm.py
│   ├── piper_tts.py
│   ├── 01_wordlist.py
│   ├── 02_ipa.py
│   ├── 03_ko.py
│   ├── 04_sentences.py
│   ├── 05_glosses.py
│   ├── 06_merge.py
│   ├── 07_audio.py
│   └── 08_site.py
├── data/
│   ├── overrides.tsv
│   ├── gloss_draft.jsonl
│   ├── gloss_overrides.jsonl
│   ├── words.json
│   ├── sentences.json
│   └── audio/
├── third_party/goethe-institute-wordlist/
├── tools/say.py
└── tts_poc/
    ├── .venv/
    ├── voices/
    └── out/
```

</details>
