# learn-german-voca — 데이터 공장(construct_dataset)과 앱(app)
#
#   make site    데이터와 오디오를 app/ 으로 옮긴다
#   make serve   app/ 을 http://localhost:8000 에 띄운다
#   make data    단어·예문·오디오까지 전부 다시 만든다 (오래 걸린다)

PORT ?= 8000

.PHONY: site serve data

site:                          ## app/data/a1.json 과 app/audio/ 를 만든다
	$(MAKE) -C construct_dataset site

serve: site                    ## 로컬 서버. 휴대폰에서는 같은 와이파이에서 이 컴퓨터 IP:8000 으로 연다
	@echo "  → http://localhost:$(PORT)"
	@ip=$$(hostname -I 2>/dev/null | awk '{print $$1}'); [ -n "$$ip" ] && echo "  → http://$$ip:$(PORT)  (같은 와이파이의 휴대폰에서)" || true
	@cd app && python3 -m http.server $(PORT) --bind 0.0.0.0

data:                          ## 텍스트 5단계 + A1 오디오
	$(MAKE) -C construct_dataset all
	$(MAKE) -C construct_dataset audio AUDIO_ARGS="--levels a1"
	$(MAKE) site
