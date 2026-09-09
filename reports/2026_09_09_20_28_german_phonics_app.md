# 서버 없는 독일어 발음 연습기

## 초보자용 단어 카드 앱 하나를 만드는 데 필요한 재료는 세 군데에 흩어져 있고, 그중 가장 골치 아픈 것은 소리다

2026년 9월 9일 | 7 min read

*Vater*라는 단어를 처음 본 학습자는 두 번 놀란다. 처음은 이 단어의 첫 글자 V가 영어의 V가 아니라 F로 소리 난다는 사실에, 두 번째는 그 사실을 확인해 줄 마땅한 도구가 없다는 사실에. 파닉스 규칙은 배웠다. 그러나 규칙은 연습 없이는 몸에 붙지 않는다. 필요한 것은 단순하다. 단어 하나가 화면에 뜨고, 읽어 본 다음, 버튼을 누르면 발음 기호와 원어민 소리와 한국어 뜻이 나타나는 것. 컴퓨터와 휴대폰에서 모두 돌아가야 하고, 서버 운영은 하고 싶지 않다.

이 정도 요구라면 주말 하나면 만들 것처럼 보인다. 앱 자체는 실제로 그렇다. 문제는 재료다. 단어, 난이도, 발음 기호, 한국어 뜻, 오디오 다섯 가지가 한 상자에 담겨 있는 데이터셋은 존재하지 않는다. 각각을 따로 구해 붙여야 하며, 다섯 중 넷은 쉽게 구해지고 하나가 유독 까다롭다. 어느 것이 까다로운지는 잠시 뒤에 밝혀진다.

## 재료 목록

가장 쉬운 것은 단어와 난이도다. 괴테 인스티투트는 시험 응시자를 위해 A1, A2, B1 등급별 공식 단어 목록(Wortliste)을 PDF로 공개한다. A1 목록은 약 650항목이고, 각 항목에는 관사와 복수형이 붙어 있다. *der Vater, die Väter* 하는 식이다. 초보자에게는 이 관사가 단어 못지않게 중요하므로 그대로 살려 두는 편이 낫다. PDF를 직접 파싱할 필요는 없다. GitHub에는 이 목록을 이미 TSV로 옮겨 놓은 리포지토리가 여럿 있으며, A1부터 B1까지 세 등급을 한 번에 담은 것도 있다. 난이도 라벨은 등급 자체가 된다.

발음 기호도 어렵지 않다. 독일어판 위키낱말사전(de.wiktionary.org)은 표제어 거의 전부에 국제음성기호(IPA)를 달아 두었고, 위키낱말사전 덤프를 기계가 읽을 수 있는 JSON으로 풀어 놓는 wiktextract 프로젝트가 그 결과물을 kaikki.org에서 배포한다. 독일어판 전체 추출본은 압축 상태로 289 MB, 풀면 2.8 GB다. 크기가 부담스럽게 들리지만, 필요한 것은 그중 650줄에서 1,300줄뿐이다. 스크립트 하나로 표제어를 대조해 IPA 필드만 뽑아내면 된다. 라이선스는 CC-BY-SA로, 개인 학습 도구에 쓰는 데 아무 제약이 없다.

한국어 뜻은 여기서부터 사람 손이 필요해지는 첫 지점이다. 위키낱말사전의 독일어 표제어에 한국어 번역이 달린 경우는 드문드문하다. 영어 뜻은 풍부하지만 그것을 원하는 것이 아니다. 현실적인 해법은 언어 모델에게 1,300개 단어의 뜻을 일괄로 쓰게 한 다음, 직접 훑어보며 어색한 것을 고치는 것이다. A1 수준 단어는 대부분 뜻이 하나이거나 둘이라 검수에 오래 걸리지 않는다. 데이터 품질에 관한 한, 이 단계에서 30분을 쓰는 것이 이후 수백 번의 학습 세션에 그대로 반영된다.

## 문제는 소리다

이제 다섯 번째 재료, 오디오 차례다. 선택지는 셋이고, 셋 다 나름의 유혹이 있다.

첫째는 브라우저에 내장된 음성 합성, 즉 Web Speech API다. 파일이 필요 없고 코드는 세 줄이다. 이것만으로 프로토타입을 오늘 밤 안에 띄울 수 있다. 그러나 이 API는 "브라우저가 가진 음성"을 쓸 뿐이어서, 어떤 목소리가 나올지는 기기가 정한다. 맥에서는 그럴듯하고, 안드로이드에서는 독일어 음성 팩이 설치되어 있지 않으면 침묵하거나 영어 음성이 독일어를 읽는 참사가 벌어진다. 리눅스 데스크톱에서는 대개 후자다. 이 프로젝트가 리눅스에서 만들어지고 있다는 점을 생각하면, 이 선택지는 개발 중 동작 확인용으로만 남겨 두는 것이 맞다.

둘째는 원어민 녹음이다. 위키미디어 커먼즈에는 독일어 발음 파일이 대량으로 있다. 특히 Lingua Libre 프로젝트를 통해 올라온 독일어 녹음만 26,112개다. 진짜 사람이 진짜로 발음한 소리라는 점에서 이보다 나은 것은 없다. 문제는 균일하지 않다는 것이다. 화자가 여럿이고, 마이크가 다르고, 음량이 제각각이며, 어떤 단어는 있고 어떤 단어는 없다. 학습자 입장에서 카드를 넘길 때마다 목소리가 바뀌고 소리 크기가 널뛰는 것은 생각보다 집중을 깨뜨린다. 커버리지도 확인해 봐야 알며, 650개 단어 중 몇 개가 비어 있을지는 파일 목록을 대조하기 전에는 말할 수 없다.

셋째는 클라우드 음성 합성으로 파일을 미리 만들어 두는 것이다. Google Cloud Text-to-Speech나 Azure Speech의 독일어 신경망 음성에 단어를 하나씩 넣고 mp3를 받아 저장한다. 요금은 걱정할 수준이 아니다. Google의 경우 WaveNet 음성은 월 100만 자까지 무료이고, 1,300개 단어를 SSML 태그까지 포함해 넉넉히 잡아도 10만 자를 넘지 않는다. 한 번 만들면 끝이며, 그 뒤로는 그냥 정적 파일이다.

이 셋째 선택지가 답인 이유는 요금이 아니라 통제력이다. 애초의 요구는 "독일어의 발음 특성이 잘 드러나는 강렬한 오디오"였다. 원어민 녹음은 자연스럽지만 자연스러운 발화는 초보자 귀에 뭉개져 들린다. 합성 음성은 SSML로 속도와 쉼을 지시할 수 있어서, 보통 속도로 한 번 들려준 뒤 0.7배속으로 한 번 더 들려주는 식의 구성이 가능하다. *Väter*의 움라우트나 *ich*의 ch처럼 한국어에 없는 소리가 두 번째 재생에서 또렷하게 분리된다. 단어 하나에 대한 SSML은 이 정도면 충분하다.

```xml
<speak>
  <prosody rate="100%">Vater</prosody>
  <break time="500ms"/>
  <prosody rate="70%">Vater</prosody>
</speak>
```

이 템플릿을 1,300번 돌리는 스크립트는 40줄이면 된다. 핵심은 API 키가 이 스크립트 안에서만 쓰이고 앱 코드에는 절대 들어가지 않는다는 점이다. 생성은 개발자 컴퓨터에서 한 번, 배포는 mp3 폴더째로.

<details>
<summary>오디오 생성 스크립트와 프로젝트 구조 펼쳐 보기</summary>

```
learn-german-voca/
├── data/
│   ├── raw/
│   │   ├── goethe_a1.tsv          # GitHub에서 받은 괴테 목록
│   │   └── de-extract.jsonl       # kaikki.org 독일어판 추출본 (git 제외)
│   └── words.json                 # 최종 병합 결과, 앱이 읽는 파일
├── scripts/
│   ├── build_words.py             # 목록 + IPA + 한국어 뜻 병합
│   └── gen_audio.py               # 아래 스크립트
├── public/
│   ├── audio/
│   │   ├── vater.mp3
│   │   └── ...
│   └── manifest.webmanifest
├── index.html
└── app.js
```

```python
# scripts/gen_audio.py
import json, pathlib
from google.cloud import texttospeech as tts

client = tts.TextToSpeechClient()
voice = tts.VoiceSelectionParams(language_code="de-DE", name="de-DE-Wavenet-B")
cfg = tts.AudioConfig(audio_encoding=tts.AudioEncoding.MP3)
out = pathlib.Path("public/audio"); out.mkdir(parents=True, exist_ok=True)

words = json.load(open("data/words.json", encoding="utf-8"))
for w in words:
    path = out / f"{w['id']}.mp3"
    if path.exists():
        continue                      # 재실행 시 이미 만든 파일은 건너뜀
    ssml = (f"<speak><prosody rate='100%'>{w['de']}</prosody>"
            f"<break time='500ms'/>"
            f"<prosody rate='70%'>{w['de']}</prosody></speak>")
    resp = client.synthesize_speech(
        input=tts.SynthesisInput(ssml=ssml), voice=voice, audio_config=cfg)
    path.write_bytes(resp.audio_content)
    print("ok", w["de"])
```

words.json의 항목 하나는 이런 모양이다.

```json
{
  "id": "vater",
  "de": "der Vater",
  "plural": "die Väter",
  "level": "A1",
  "ipa": "ˈfaːtɐ",
  "ko": "아버지"
}
```

</details>

## 서버는 없어도 된다

재료가 모두 정적 파일이라는 사실이 마지막 두 질문에 동시에 답한다. 데이터셋은 바뀌지 않고, 사용자는 한 사람이며, 오디오는 이미 만들어져 있다. 런타임에 서버가 할 일이 없다. 학습 진행 상태, 그러니까 어떤 단어를 봤고 어떤 단어에서 막혔는지는 브라우저의 localStorage에 넣으면 되고, 그 정도 데이터는 수 KB다.

그러므로 앱은 정적 웹앱 하나로 만든다. 프레임워크 없이 HTML과 자바스크립트 한 파일씩이면 되고, 익숙하다면 Svelte에 Vite를 붙이는 정도가 상한이다. 컴퓨터와 휴대폰을 따로 만들 이유는 없다. 웹 매니페스트 하나를 추가하면 휴대폰 홈 화면에 앱처럼 설치되고, 서비스 워커를 붙이면 오프라인에서도 돈다. 이것을 PWA라 부르는데, 이름이 거창할 뿐 실체는 파일 두 개다. 배포는 GitHub Pages나 Cloudflare Pages에 올리면 무료이고 HTTPS는 자동으로 따라온다. 오디오는 mp3 기준 단어당 10 KB 안팎이라 전체를 합쳐도 15 MB 남짓이며, 정적 호스팅 한도 안에 넉넉히 들어간다.

서버가 필요해지는 순간은 하나뿐이다. 여러 기기에서 학습 진행 상태를 동기화하고 싶어질 때. 그날이 오면 localStorage를 작은 키-값 저장소로 바꾸면 되고, 그 전까지는 서버라는 단어를 잊어도 좋다.

정리하면 순서는 이렇다. 괴테 목록 TSV를 받고, kaikki.org 추출본에서 IPA를 대조해 붙이고, 언어 모델로 한국어 뜻을 채운 뒤 검수하고, SSML 템플릿으로 mp3를 일괄 생성하고, JSON 하나와 mp3 폴더를 정적 페이지에 담아 올린다. 다섯 단계 중 넷은 스크립트가 하고, 사람이 할 일은 한국어 뜻을 읽어 보는 30분이다. *Vater*의 V가 F로 들리는 순간은 그 뒤에 온다. ■

---

출처
- [Goethe-Zertifikat A1 Wortliste (PDF)](https://www.goethe.de/pro/relaunch/prf/de/A1_SD1_Wortliste_02.pdf)
- [ilkermeliksitki/goethe-institute-wordlist, A1·A2·B1 TSV](https://github.com/ilkermeliksitki/goethe-institute-wordlist)
- [kaikki.org 독일어판 위키낱말사전 원본 추출 데이터](https://kaikki.org/dewiktionary/rawdata.html)
- [tatuylonen/wiktextract](https://github.com/tatuylonen/wiktextract)
- [Wikimedia Commons, Category:German pronunciation](https://commons.wikimedia.org/wiki/Category:German_pronunciation)
- [Google Cloud Text-to-Speech 요금](https://cloud.google.com/text-to-speech/pricing)
