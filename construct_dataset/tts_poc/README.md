# 즉석 Piper TTS

Piper 합성 코드는 `scripts/piper_tts.py`로 옮겼고, 이 디렉터리는 기존 전용
가상환경과 음성 모델을 보관한다. 임의의 독일어를 듣는 CLI는 `tools/say.py`다.

```bash
./setup.sh
.venv/bin/python ../tools/say.py Vater "das Mädchen"
.venv/bin/python ../tools/say.py --file sample_words.txt --alignments
```

기존 `synth.py` 명령도 호환용 진입점으로 계속 동작한다. 즉석 도구는 입력
텍스트를 ASCII 슬러그로 바꿔 `out/`에 저장하지만, 그 이름은 앱이나
데이터셋에서 사용하지 않는다. 정식 데이터 오디오는 `make audio`가
`words.json`과 `sentences.json`의 id를 그대로 받아 `data/audio/`에 만든다.

`.venv/`, `voices/`, `out/`은 커밋하지 않는다.
