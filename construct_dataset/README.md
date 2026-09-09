# construct_dataset

괴테 인스티투트 A1·A2·B1 단어 목록(Wortliste)에 독일어판 위키낱말사전의 발음 기호와
언어 모델이 쓴 한국어 뜻을 붙여 `data/words.json` 하나로 만든다. 앱은 이 파일만 읽는다.

```
make setup            # uv 가상환경, anthropic·pydantic, 단어 목록 서브모듈
make all              # 1~4단계. 2단계는 kaikki.org 덤프(303 MB)를 data/raw/ 에 받는다
make ko KO_ARGS="--levels a1 --model sonnet --workers 4"   # 3단계만, A1 만
```

## 단계

| 단계 | 스크립트 | 입력 | 출력 | 사람 손 |
|---|---|---|---|---|
| 1 단어·난이도 | `scripts/01_wordlist.py` | `third_party/goethe-institute-wordlist/*/*.tsv` | `data/wordlist.jsonl` | 없음 |
| 2 발음 기호 | `scripts/02_ipa.py` | `data/raw/raw-wiktextract-data.jsonl.gz` | `data/ipa.jsonl`, `data/kaikki_matches.jsonl` | 없음 |
| 3 한국어 뜻 | `scripts/03_ko.py` | 1·2단계 출력 | `data/ko_draft.tsv` | 검수 |
| 4 병합 | `scripts/04_merge.py` | 위 전부 + `data/overrides.tsv` | `data/words.json`, `data/review_queue.tsv`, `data/stats.json` | 없음 |

3단계는 `ANTHROPIC_API_KEY` 가 있으면 Anthropic SDK 로, 없으면 로컬 `claude` CLI 로 돈다.
모델은 `--model` 로 고른다. 이 일은 스키마가 좁고 출력이 짧아 `sonnet` 이면 충분하다.
같은 id 는 두 번 묻지 않으므로 중간에 끊겨도, 모델을 바꿔도, 다시 실행하면 이어서 한다.

## 검수

`data/review_queue.tsv` 에 사람이 봐야 할 항목이 이유와 함께 모인다.
고칠 것은 `data/overrides.tsv` 에 같은 id 로 적는다. article, plural, ipa, ko, note 중 채운 칸만 이긴다.
그 다음 `make merge`.

## 출처

- 단어 목록: [ilkermeliksitki/goethe-institute-wordlist](https://github.com/ilkermeliksitki/goethe-institute-wordlist) (괴테 인스티투트 공식 PDF 를 TSV 로 옮긴 것, 서브모듈)
- 발음 기호·복수형·관사: [kaikki.org 독일어판 위키낱말사전 추출본](https://kaikki.org/dewiktionary/rawdata.html), CC BY-SA 4.0
- 한국어 뜻: 언어 모델 초안 + 사람 검수
