# 단어가 소리를 내는 곳

## 괴테 A1 단어 679개를 화면에 하나씩 띄우고, 읽어 본 다음, 눌러서 확인한다

`construct_dataset/` 이 재료를 만든다면 `src/`는 그것을 먹는 Svelte 앱이고,
`app/`은 빌드된 정적 사이트다. 화면은 기능별 Svelte 컴포넌트로 나뉘고 학습
일정·검색·저장 로직은 `src/lib/`의 TypeScript 모듈에 있다.

단어가 뜨면 소리 내어 읽는다. 그다음 카드를 누르면 발음 기호와 원어민 속도의
소리, 한국어 뜻, 그 단어가 실제로 쓰인 예문이 한꺼번에 나온다. 단어 소리는 보통
속도로 한 번, 0.5초 쉬고 느린 속도로 한 번 더 난다. *Vater* 의 V 가 F 로 들리는
자리는 두 번째 재생에서 또렷해진다.

## 띄우기

저장소 루트에서 한 줄이면 된다.

```bash
npm install
npm run dev
```

배포 결과를 확인하려면 `make serve`를 쓴다. 이 명령은 앱을 빌드하고 데이터와
오디오를 `app/`으로 옮긴 뒤 `http://localhost:8000`에 띄운다. 브라우저에서
`file://`로 `index.html`을 열면 단어 파일을 읽지 못한다.

데이터만 다시 깔고 싶으면 `make -C construct_dataset site`를 쓴다.

## 화면 셋

**연습.** 카드가 하나씩 나온다. 한 세션은 기본 20개이고 톱니바퀴에서 바꾼다.
익힌 정도는 라이트너 상자로 관리한다. 맞히면 한 칸 올라가 1일, 3일, 1주, 2주,
한 달 뒤에 다시 나오고, 틀리면 처음 칸으로 돌아와 그 세션 안에서 다시 만난다.

**단어장.** 679개를 전부 훑고 찾는다. `Bäckerei` 를 `backerei` 로 쳐도 걸린다.
한글 자판에서 움라우트를 치기 어렵기 때문이고, `baeckerei` 와 `strasse` 도 같은
이유로 걸리게 해 두었다. 줄 오른쪽 점의 색이 그 단어의 익힘 단계다.

**진도.** 얼마나 봤고 얼마나 익혔는지, 그리고 오디오를 통째로 받아 두는 단추가
있다.

데스크톱에서는 손을 마우스로 옮기지 않아도 된다. <kbd>Space</kbd> 로 확인하고
<kbd>1</kbd> 과 <kbd>2</kbd> 로 채점하며 <kbd>P</kbd> 로 다시 듣는다.

## 휴대폰에 설치하기

주소를 연 뒤 브라우저 메뉴에서 홈 화면에 추가하면 주소창 없는 앱처럼 열린다.
이때 필요한 것은 `manifest.webmanifest` 와 `sw.js` 두 파일뿐이다.

소리까지 오프라인으로 쓰려면 진도 화면에서 **오디오 전부 내려받기** 를 누른다.
A1 오디오 3,264개, 약 26 MB다. 화면과 단어 파일은 처음 열 때 이미 저장되므로
이 단추를 누르지 않아도 글자는 비행기 안에서 나온다. 소리만 나지 않을 뿐이다.

캐시를 둘로 나눈 이유가 여기 있다. 26 MB를 첫 방문에 받게 하지 않으려는 것이다.
누르지 않아도 한 번 재생한 소리는 그때그때 저장된다.

## 어디에 무엇이 남는가

학습 기록은 브라우저의 localStorage 에만 있다. 서버로 가지 않고 기기 밖으로
나가지 않는다. 그래서 컴퓨터에서 익힌 것과 휴대폰에서 익힌 것은 서로 모른다.
지우려면 진도 화면 맨 아래 단추를 쓴다.

| 열쇠 | 내용 |
|---|---|
| `lgv.progress.a1` | 단어별 익힘 상자, 다음에 볼 때, 본 횟수 |
| `lgv.settings` | 자동 재생·영어 표시·세션 분량 |

## 올리기

`npm run build`가 `app/` 폴더에 배포할 정적 사이트를 만든다.

```bash
make site                 # app/data 와 app/audio 를 채운다
npx wrangler pages deploy app     # 또는 GitHub Pages, Netlify, 무엇이든
```

`app/audio/` 는 `construct_dataset/data/audio/` 와 같은 파일을 가리키는
하드링크다. 디스크를 두 배로 쓰지 않지만 보통의 파일이므로 `cp` 든 `rsync` 든
그대로 복사된다. 두 폴더는 `make site` 가 언제든 다시 만들 수 있어서 git 에
넣지 않는다. 올릴 때는 반드시 `make site` 를 먼저 실행할 것.

## A1 뿐인 이유

단어와 뜻은 A1·A2·B1 3,005개가 모두 준비되어 있다. 없는 것은 소리다. A2와 B1의
mp3 6,158개를 아직 만들지 않았다. 만들고 나면 이렇게 한 줄씩 늘리면 된다.

```bash
make -C construct_dataset audio AUDIO_ARGS="--levels a2,b1"
make -C construct_dataset site SITE_ARGS="--levels a1,a2,b1"
```

`app/data/` 에 `a2.json` 과 `b1.json` 이 생긴다. 앱이 등급을 고르게 하는 일은
그다음이다. 지금 `src/lib/constants.ts`의 `LEVEL`이 그 자리를 잡아 두고 있다.

<details>
<summary>파일 구조 펼쳐 보기</summary>

```text
src/
├── App.svelte              앱 상태·라우팅·재생 조율
├── components/             연습·단어장·진도·상세 화면
├── lib/                    타입·라이트너 일정·검색·저장
└── app.css                 휴대폰 우선 스타일
app/
├── index.html              Vite가 만든 진입 문서
├── assets/                 묶고 최적화한 JavaScript와 CSS
├── sw.js                   셸 캐시와 오디오 캐시를 나눠 쓴다
├── manifest.webmanifest    홈 화면 설치
├── icon.svg · icon-192.png · icon-512.png
├── data/                   make site 가 만든다
│   ├── a1.json             단어 679, 예문 2,585. 548 KB
│   └── levels.json
└── audio/                  make site 가 하드링크한다. mp3 3,264개, 26 MB
```

| 파일 | 만드는 것 |
|---|---|
| `construct_dataset/scripts/05_merge.py` | `words.json`, `sentences.json` |
| `construct_dataset/scripts/06_audio.py` | `data/audio/{id}.mp3` |
| `construct_dataset/scripts/07_site.py` | `app/data/{등급}.json`, `app/audio/` |

</details>
