# construct_dataset — 단어·예문 텍스트와 로컬 발음 오디오를 만드는 6단계 파이프라인
#
#   make setup      텍스트 파이프라인 가상환경·의존성·서브모듈
#   make all        1~5단계 (3·4단계는 API 키 또는 claude CLI 필요)
#   make ipa        2단계만. 덤프(303 MB)가 없으면 받는다.
#   make ko KO_ARGS="--levels a1 --model sonnet --workers 4"
#   make sentences SENTENCE_ARGS="--levels a1 --model sonnet --workers 4"
#   make audio AUDIO_ARGS="--levels a1"  # 별도 TTS 환경을 준비하고 mp3 32k 생성

PY            := .venv/bin/python
AUDIO_PY      := tts_poc/.venv/bin/python
AUDIO_READY   := tts_poc/.venv/.requirements-audio-installed
KAIKKI        := data/raw/raw-wiktextract-data.jsonl.gz
KAIKKI_URL    := https://kaikki.org/dewiktionary/raw-wiktextract-data.jsonl.gz
KO_ARGS       ?=
SENTENCE_ARGS ?=
AUDIO_ARGS    ?= --levels a1

.PHONY: all setup setup-audio wordlist ipa ko sentences merge audio clean

all: wordlist ipa ko sentences merge

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

sentences:                     ## 4단계: 언어 모델 → sentence_draft.tsv (--effort low 기본)
	$(PY) scripts/04_sentences.py $(SENTENCE_ARGS)

merge:                         ## 5단계: → words.json, sentences.json, review_queue.tsv, stats.json
	$(PY) scripts/05_merge.py

$(AUDIO_READY): requirements-audio.txt
	if [ ! -x $(AUDIO_PY) ]; then uv venv tts_poc/.venv --python 3.13; fi
	uv pip install --python $(AUDIO_PY) -r requirements-audio.txt
	$(AUDIO_PY) tools/say.py --download-only
	touch $@

setup-audio: $(AUDIO_READY)    ## Piper 전용 가상환경·음성 모델. 텍스트 환경과 합치지 않는다

audio: merge $(AUDIO_READY)    ## 6단계: words/sentences의 id.mp3 (기본 A1, mp3 32k)
	$(AUDIO_PY) scripts/06_audio.py $(AUDIO_ARGS)

clean:                         ## 모델 초안·덤프·생성 비용이 큰 오디오는 지우지 않는다
	rm -f data/wordlist.jsonl data/ipa.jsonl data/kaikki_matches.jsonl data/words.json data/sentences.json data/review_queue.tsv data/stats.json
