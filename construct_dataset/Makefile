# construct_dataset — 괴테 단어 목록 + 위키낱말사전 IPA + 언어 모델 한국어 뜻 → data/words.json
#
#   make setup      가상환경·의존성·서브모듈
#   make all        1~4단계 전부 (3단계는 API 키 또는 claude CLI 필요)
#   make ipa        2단계만. 덤프(303 MB)가 없으면 받는다.
#   make ko KO_ARGS="--levels a1 --model sonnet --workers 4"

PY         := .venv/bin/python
KAIKKI     := data/raw/raw-wiktextract-data.jsonl.gz
KAIKKI_URL := https://kaikki.org/dewiktionary/raw-wiktextract-data.jsonl.gz
KO_ARGS    ?=

.PHONY: all setup wordlist ipa ko merge clean

all: wordlist ipa ko merge

setup:
	uv venv .venv --python 3.13
	uv pip install --python $(PY) -r requirements.txt
	git submodule update --init third_party/goethe-institute-wordlist

wordlist:                      ## 1단계: TSV → wordlist.jsonl
	$(PY) scripts/01_wordlist.py

$(KAIKKI):
	mkdir -p data/raw
	curl -L -C - --retry 5 --retry-delay 3 -o $@ $(KAIKKI_URL)

ipa: $(KAIKKI)                 ## 2단계: 덤프 → ipa.jsonl
	$(PY) scripts/02_ipa.py

ko:                            ## 3단계: 언어 모델 → ko_draft.tsv (이미 있는 id 는 건너뜀. --model 로 모델 선택)
	$(PY) scripts/03_ko.py $(KO_ARGS)

merge:                         ## 4단계: → words.json, review_queue.tsv, stats.json
	$(PY) scripts/04_merge.py

clean:                         ## 모델 초안(ko_draft.tsv)과 덤프는 지우지 않는다
	rm -f data/wordlist.jsonl data/ipa.jsonl data/kaikki_matches.jsonl data/words.json data/review_queue.tsv data/stats.json
