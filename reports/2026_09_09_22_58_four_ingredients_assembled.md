# 가장 쉬운 재료가 가장 지저분했다

## 단어, 난이도, 발음 기호, 한국어 뜻을 붙이는 스크립트 네 개를 만들었다. 2.8 GB짜리 사전 덤프는 8초 만에 끝났고, 63 KB짜리 단어 목록이 오후를 가져갔다

2026년 9월 9일 오후 11시 | 12 min read

첫 보고서는 재료가 다섯이고 그중 넷은 쉽게 구해진다고 썼다. 이번에는 그 넷을 실제로 붙여 보았다. 주장 자체는 맞았다. 넷 다 하루 안에 붙었다. 다만 어느 쪽이 쉬울지를 파일 크기로 짐작한 것은 틀렸다.

풀면 2.8 GB가 된다며 크기가 부담스럽게 들린다고 적었던 위키낱말사전 덤프는, 스크립트가 8초 만에 훑었다. 반면 GitHub에서 받은 괴테 인스티투트 단어 목록은 A1 파일이 63 KB밖에 안 되는데도 파싱 규칙을 세 번 고쳐 쓰게 만들었다. 이유는 분명하다. 덤프는 기계가 기계에게 넘기려고 만든 파일이고, 단어 목록은 사람이 PDF를 보고 손으로 옮긴 파일이다. 데이터의 무게는 바이트가 아니라 사람 손을 몇 번 거쳤느냐로 잰다.

결과물은 `construct_dataset/` 아래에 있다. 스크립트 네 개가 차례로 돌아 `data/words.json` 하나를 만든다. 항목은 3,005개다.

## 목록이 제일 지저분하다

괴테 인스티투트의 A1·A2·B1 목록을 TSV로 옮겨 둔 리포지토리를 git 서브모듈로 가져왔다. 파일은 등급별, 알파벳별로 쪼개져 있고 한 줄은 세 칸이다. 표제어, 독일어 예문, 영어 번역. 세 등급을 합치면 7,377줄이다.

문제는 첫 칸이다. 관사, 복수형, 동사 변화형, 뜻 번호가 전부 한 문자열에 뭉쳐 있다.

```
der Vater, -ä              die Adresse,-en           das Buch, -ü, er(1)
der Apfel, ¨-              die Ankunft, -¨e          das Studium, Studien
abholen(1)   abholen(2)    (sich) vorstellen         sein, ist, war, ist gewesen
```

복수형 힌트로 쓰인 서로 다른 문자열이 93가지다. 원본 PDF는 움라우트를 위첨자 점 두 개로 적는데, 이것을 손으로 옮긴 사람은 *das Dorf*에서는 `¨-er`로, *die Ankunft*에서는 `-¨e`로, *das Fahrrad*에서는 `-ä, er`로 썼다. 셋은 같은 것을 가리킨다. 첫 보고서는 관사가 단어 못지않게 중요하니 그대로 살려 두자고 했다. 여기서는 한 걸음 더 간다. 학습 카드에 `-ä`를 띄울 수는 없으니 힌트를 실제 복수형으로 펴야 한다. *der Vater, -ä*는 *die Väter*가 되어야 한다.

움라우트를 어디에 찍을지는 규칙 하나로 끝났다. 어간의 마지막 a, o, u에 찍되 au는 통째로 äu가 된다. Vater→Väter, Bahnhof→Bahnhöfe, Tochter→Töchter, Baum→Bäume가 전부 이 한 줄에서 나온다.

```python
def umlaut(stem: str) -> str | None:
    """마지막 a/o/u/au 에 움라우트를 찍는다. Vater→Väter, Baum→Bäum(e), Bahnhof→Bahnhöf(e)."""
    for i in range(len(stem) - 1, -1, -1):
        ch = stem[i]
        if ch == "u" and i > 0 and stem[i - 1] in "aA":
            return stem[: i - 1] + UMLAUT[stem[i - 1]] + "u" + stem[i + 1:]
        if ch in UMLAUT:
            return stem[:i] + UMLAUT[ch] + stem[i + 1:]
    return None
```

말썽은 어미를 붙이는 쪽이었다. 목록은 *Adresse*에도 `-en`이라 적어 두었는데 독일어에 *Adresseen*은 없다. *Datum, -en*은 *Daten*이지 *Datumen*이 아니고, *Museum*은 *Museen*, *Praktikum*은 *Praktika*다. 라틴어에서 온 어미를 갈아 끼우는 규칙을 넣었더니 이번에는 *Baum*이 라틴어 취급을 받아 *Bäe*가 되었다. `-um`으로 끝나기는 하나 그 um은 어미가 아니라 어간의 일부였던 것이다. 세 번째 판이 아래 것이고, 이제 스무 개짜리 표본에서 전부 맞는다.

```python
def join_suffix(stem: str, suf: str) -> str:
    """어미를 붙인다. 목록은 -e 로 끝나는 말에도 '-en' 이라 적고, 라틴어계 어미는 갈아 끼워야 한다.

    Adresse+en → Adressen   Datum+en → Daten   Praktikum+a → Praktika
    Thema+en → Themen       Konto+en → Konten  Praxis+en → Praxen     Bäum+e → Bäume (aum 은 라틴어 어미가 아니다)
    """
    if not suf:
        return stem
    if stem.endswith("um") and not stem.endswith(("aum", "äum")) and (suf.startswith("e") or suf == "a"):
        return stem[:-2] + suf
    if stem.endswith(("a", "o")) and suf == "en":
        return stem[:-1] + suf
    if stem.endswith("is") and suf == "en":
        return stem[:-2] + suf
    if stem.endswith("e") and suf.startswith("e"):
        return stem + suf[1:]
    return stem + suf
```

표제어의 나머지 장식은 벗겨 낸다. *abholen(1)*과 *abholen(2)*는 같은 단어에 예문이 둘 달린 것이므로 항목 하나로 합치고 예문만 모은다. *(sich) vorstellen*은 *vorstellen*으로, *(Kredit)-Karte*는 *Kreditkarte*로 바꿔 사전에서 찾되 카드에는 원래 표기를 그대로 보여 준다. 예문 칸이 빈 줄 35개는 버렸다. 전부 *hat gechattet*, *ist dabei gewesen* 같은 것들로, PDF에서 동사 변화형이 줄바꿈 때문에 제 줄로 떨어져 나온 조각이었다.

등급 처리에는 판단이 하나 들어간다. 괴테의 목록은 누적이다. A2에는 A1 단어가 대부분 다시 나오고 B1에는 둘 다 나온다. 같은 단어로 카드를 세 장 만들 이유가 없으니 표제어와 관사가 같으면 처음 나온 등급 하나로 합쳤다. 1,126개가 두 등급 이상에 걸쳐 있었고, 합치고 나니 3,005개다. A1이 679개, A2에서 새로 들어온 것이 607개, B1에서 1,719개. 항목의 id는 등급이 아니라 단어에서 만든다. 괴테가 다음 개정판에서 어떤 단어를 A1에서 A2로 옮기더라도 학습 기록은 살아남아야 하기 때문이다.

## 2.8 GB는 8초면 된다

kaikki.org가 배포하는 독일어판 위키낱말사전 추출본은 303 MB짜리 gzip이고, 풀면 2.8 GB에 1,329,116줄이다. 한 줄이 표제어와 품사의 조합 하나에 대한 JSON이다.

이것을 풀지 않는다. 파이썬 gzip 모듈로 한 줄씩 흘려 읽되, JSON으로 파싱하기 전에 줄 머리 400자 안에서 정규식으로 `"word"` 값만 먼저 본다. 우리 목록에 없는 단어면 그 줄은 파싱하지 않고 버린다. 130만 줄 가운데 실제로 파싱하는 것은 3,684줄뿐이고, 그래서 8초다. 첫 보고서가 "크기가 부담스럽게 들리지만 필요한 것은 그중 650줄에서 1,300줄뿐"이라고 한 직관은 옳았다. 다만 그 직관을 코드로 옮기려면 파싱 자체를 건너뛰어야 한다는 조건이 붙는다.

```python
    with gzip.open(gz_path, "rt", encoding="utf-8") as f:
        for line in f:
            n_lines += 1
            m = WORD_RE.search(line, 0, 400) or WORD_RE.search(line)
            if not m:
                continue
            w = m.group(1)
            if "\\" in w:
                w = json.loads(f'"{w}"')
            if w not in wanted:
                continue
            rec = json.loads(line)
            if rec.get("lang_code") != "de":
                continue
            n_hit += 1
            yield slim(rec)
```

찾은 뒤가 오히려 성가시다. 같은 철자에 줄이 여럿 딸릴 수 있다. *sein*은 동사 페이지와 소유대명사 페이지가 따로 있고, *Väter*는 명사 페이지이긴 하나 태그에 form-of가 붙은 변화형 페이지이며, *Entschuldigung*은 명사이면서 감탄사다. *das Fahrrad/Rad*처럼 목록이 후보를 둘 적어 둔 경우도 있다. 그래서 줄마다 점수를 매겨 하나를 고른다. 변화형 페이지는 크게 깎고, 표제어에 관사가 있으면 명사 페이지를 우대하고, 사전이 아는 관사가 목록의 관사와 같으면 조금 더 주고, 목록이 먼저 적은 후보를 뒤의 것보다 앞세운다.

```python
def score(entry: dict, rec: dict, key_rank: int) -> int:
    s = 0
    if "form-of" in rec["tags"]:
        s -= 100                     # Väter, möchten(변화형) 같은 페이지
    if any(clean_ipa(x) for x in rec["ipa"]):
        s += 20
    if entry["article"]:
        s += 10 if rec["pos"] == "noun" else 0
        if entry["article"] in rec["articles"]:
            s += 5
    elif rec["pos"] == "noun":
        s -= 2                       # 관사 없는 표제어가 명사 페이지와 겹치면 (Achtung) 약간만 밀어 둔다
    s += min(rec["n_senses"], 5)
    s -= 10 * key_rank               # lookup_keys 앞쪽 후보가 우선. Fahrrad/Rad 에서 Fahrrad 가 이겨야 한다
    return s
```

이렇게 해서 3,005개 중 2,950개에 발음 기호가 붙었다.

| 등급 | 항목 | IPA 있음 | 비율 |
|---|---|---|---|
| A1 | 679 | 673 | 99.1% |
| A2 | 607 | 591 | 97.4% |
| B1 | 1,719 | 1,686 | 98.1% |

빠진 55개는 대체로 사전에 표제어가 있을 리 없는 것들이다. *weg sein*, *Bescheid geben*, *um … zu* 같은 여러 낱말짜리 표현, *ander-*, *un-*, *Schwieger-* 같은 접두 조각, *Rüebli*, *Poulet*, *Matura* 같은 스위스·오스트리아 지역어. 그리고 *Geburts-(jahr*처럼 TSV를 만들 때 쉼표에서 잘려 나간 표제어 몇 개.

덤프 한 줄에는 발음 기호 말고도 관사, 복수형, 위키미디어 커먼즈 녹음 파일의 URL이 들어 있다. 이것을 버리지 않은 덕에 검산이 공짜로 생겼다. 1단계에서 힌트를 펴 만든 복수형 1,032개를 사전 쪽과 대조했더니 어긋난 것이 여섯 개 남았다. *die Bank*는 Banken(은행)과 Bänke(벤치)가 둘 다 맞고 *das Wort*도 Wörter와 Worte가 쓰임이 다르니 사람이 봐야 한다. 그리고 목록의 오타 하나, *die Chefin, -ne*. 관사가 어긋난 것은 열둘인데 그중 셋은 목록이 *der Friseurin*, *der Schülerin*, *der Sekretärin*이라 적어 둔 것이고 나머지는 *der Beamte*처럼 형용사에서 온 명사라 사전이 여성형 페이지로 답한 것이다. 힌트가 아예 없던 명사 486개는 사전의 복수형을 그대로 받았다.

녹음 URL은 첫 보고서가 남긴 물음표 하나를 지운다. 커먼즈 녹음이 단어 몇 개를 덮는지는 파일 목록을 대조하기 전에는 말할 수 없다고 썼는데, 답은 "발음 기호가 있는 단어 거의 전부"다. 2,950개 중 2,946개에 mp3 URL이 함께 왔다. 그렇다고 녹음을 쓰겠다는 뜻은 아니다. 화자와 음량이 제각각이라는 문제는 그대로이고, 오디오는 이미 노트북에서 만들기로 정해졌다. 다만 합성 음성이 이상하게 들리는 단어를 사람 목소리와 대조해 볼 수 있게 되었고, 그 URL은 `data/ipa.jsonl`에 남겨 두었다.

## 한국어 뜻은 60개씩 묻는다

세 번째 스크립트는 언어 모델을 부른다. 백엔드는 둘이다. `ANTHROPIC_API_KEY`가 있으면 Anthropic SDK로 부르고, 없으면 이 컴퓨터에 깔린 Claude Code를 `claude -p`로 부른다. 이 컴퓨터에는 키가 없고 구독은 있으니 이번 실행은 뒤의 것이었다. 어느 쪽이든 JSON 스키마로 출력 형식을 강제한다. 모델이 쓴 문장에서 뜻을 긁어내는 코드는 이 프로젝트에 없다.

CLI 쪽에는 함정이 하나 있었다. 아무 옵션 없이 `claude -p`를 부르면 Claude Code가 자기 시스템 프롬프트 3만 토큰을 앞에 붙인다. 단어 두 개의 뜻을 묻는 시험 호출에 정가 기준 63센트가 나갔다. `--system-prompt`로 우리 프롬프트만 쓰게 하고 `--tools ""`로 도구를 전부 끄자 같은 호출이 3센트가 되었다. 스무 배다.

프롬프트에는 단어마다 표제어, 등급, 위키낱말사전이 알려 준 품사, 예문 최대 넷을 JSON으로 넘긴다. 예문이 결정적이다. *abholen*에 "Wann kann ich den Schrank abholen?"과 "Wir müssen meinen Bruder abholen"이 함께 가면 모델은 "찾아오다"와 "데리러 가다"를 둘 다 쓴다. 예문 없이 단어만 주면 둘 중 하나만 나온다.

```python
SYSTEM = """\
너는 독일어-한국어 학습용 단어장의 편집자다. 괴테 인스티투트 A1~B1 단어 목록의 항목을 JSON으로 받아
각 항목에 한국어 뜻(ko)과 짧은 메모(note)를 단다.

ko 규칙
- 사전 표제어처럼 짧게. 문장이나 설명이 아니라 뜻만. 흔한 뜻 1~3개를 쉼표로 구분한다.
  예: "아버지" / "데리러 가다, 찾아오다" / "오래된, 늙은"
- 예문에 쓰인 뜻을 반드시 넣고, 예문이 여러 개면 그 뜻들을 앞에 둔다.
- 명사는 명사형, 동사는 '-다' 기본형, 형용사는 '-한/-ㄴ' 꼴, 부사·전치사·접속사는 기능이 드러나는
  우리말("~부터", "그러나", "아마도").
- 독일어 단어, 관사, 복수형, 괄호 설명은 ko에 쓰지 않는다.

note 규칙
- 학습자가 꼭 알아야 할 것만 20자 이내. 예: "재귀동사", "복수형만 씀", "분리동사", "구어",
  "예문은 관용구", "장소 이동은 4격". 없으면 빈 문자열.

출력은 스키마대로 JSON만. id는 입력 그대로 돌려주고, 항목을 빼거나 더하지 않는다."""
```

호출부는 짧다. 한 묶음에 60개를 보내고, 스키마에 맞는 JSON을 받아 pydantic으로 검증한다.

```python
def call_cli(prompt: str, model: str | None) -> tuple[KoBatch, str]:
    cmd = ["claude", "-p", "--no-session-persistence", "--tools", "",
           "--system-prompt", SYSTEM, "--output-format", "json", "--json-schema", json.dumps(SCHEMA)]
    if model:
        cmd += ["--model", model]
    cmd.append(prompt)
    env = {k: v for k, v in os.environ.items() if k != "CLAUDECODE"}   # 세션 안에서 돌려도 되게
    proc = subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=900)
    if proc.returncode != 0:
        raise RuntimeError(f"claude exit {proc.returncode}: {proc.stderr.strip()[:400]}")
    data = json.loads(proc.stdout)
    if data.get("is_error") or data.get("structured_output") is None:
        raise RuntimeError(f"claude error: {str(data.get('result'))[:400]}")
    used = [m for m in data.get("modelUsage", {}) if not m.startswith("claude-haiku")]   # haiku 는 보조 호출
    return KoBatch.model_validate(data["structured_output"]), (used[0] if used else (model or "claude-code-default"))
```

받은 답에서 빠진 id는 모아 두었다가 한 번 더 묻는다. 결과는 묶음이 끝날 때마다 `data/ko_draft.tsv`에 바로 쓰고, 다시 실행하면 이미 있는 id는 건너뛴다.

이 설계가 곧바로 값을 했다. 900개를 만든 시점에 비용이 눈에 띄어 모델을 Claude Fable에서 Sonnet으로 갈아 끼웠는데, 앞서 만든 900개는 그대로 두고 남은 2,105개만 이어서 돌렸다. Sonnet 쪽은 11분 걸렸다. 두 모델이 쓴 뜻을 나란히 놓고 봐도 차이를 집어내기 어렵다. 애초에 이 일은 스키마가 좁고 출력이 짧다. 단어 하나에 우리말 몇 마디를 다는 작업에 가장 비싼 모델을 쓸 이유가 없었다.

3,005개 전부에 뜻이 붙었다. 세 등급 모두 100퍼센트이고, 실패한 묶음도 재시도 뒤에 남은 빈칸도 없다. 결과는 이런 모양이다.

```
der Vater	아버지	복수 Väter
abholen	데리러 가다, 찾아오다	분리동사
müssen	~해야 한다	화법조동사, ich muss
laufen	걷다, 달리다, 상영되다	sein 완료, 강변화
die Jeans	청바지	복수형만 씀
kalt	추운, 차가운	Mir ist kalt: 3격
```

note 칸은 있으면 좋겠다 싶어 넣었는데 생각보다 쓸모가 있다. 분리동사인지, 완료형을 sein으로 만드는지, 재귀동사인지를 모델이 알아서 적는다. 카드 뒷면에 한 줄 더 들어갈 자리가 생겼다.

## 사람이 볼 것은 73줄이다

네 번째 스크립트가 앞의 셋을 합치면서, 사람이 봐야 할 항목을 이유와 함께 `data/review_queue.tsv`에 모은다. 발음 기호가 없는 것 55개, 복수형이 사전과 어긋난 것 6개, 관사가 어긋난 것 12개. 겹치는 항목이 없어 딱 73줄이다.

고칠 것은 `data/overrides.tsv`에 같은 id로 적는다. 열은 article, plural, ipa, ko, note이고 채운 칸만 자동 생성값을 이긴다. 다시 합치면 그 항목은 검수 목록에서 사라진다. 원본 TSV나 중간 산출물을 손으로 고치지 않는 것이 요점이다. 서브모듈을 갱신하거나 스크립트를 고쳐 전체를 다시 만들어도 사람이 한 일은 그대로 남는다.

검수 목록에 없는 것도 읽어는 봐야 한다. 첫 보고서가 말한 "30분"이 이 일인데, 그 견적은 이제 맞지 않는다. 3,005줄을 훑는 데 30분은 부족하다. A1 679줄이라면 맞다. 그러니 순서는 A1을 먼저 읽고, 앱이 A1로 돌기 시작한 뒤에 A2와 B1을 읽는 것이다. 초안이 어긋나는 방식은 대체로 하나다. 뜻이 틀리기보다 뜻이 너무 많다. 뜻을 셋 이상 단 항목이 408개, 전체의 14퍼센트다. *die Straße*의 "길, 거리, 도로"는 셋 다 맞지만 카드 뒷면에는 하나면 된다. 프롬프트에 "1~3개"라고 적은 대가이고, 사람이 지우는 편이 모델에게 더 조이라고 말하는 것보다 빠르다.

## words.json

최종 파일의 항목 하나는 이런 모양이다.

```json
{
  "id": "vater",
  "de": "der Vater",
  "lemma": "Vater",
  "article": "der",
  "plural": "die Väter",
  "level": "A1",
  "ipa": "ˈfaːtɐ",
  "ko": "아버지",
  "note": "복수 Väter",
  "pos": "Substantiv",
  "examples": [{"de": "Mein Vater ist Arbeiter.", "en": "My father is a worker."}]
}
```

첫 보고서가 그린 모양에서 lemma, note, pos, examples가 늘었다. 예문은 다 합쳐 6,580개이고 항목 절반 이상이 둘 이상을 가진다. 카드 앞면에 단어 대신 예문을 띄우는 연습 모드가 덤으로 생긴 셈이다.

전체를 다시 만드는 명령은 셋이다.

```
make setup     # uv 가상환경, anthropic·pydantic, 서브모듈
make all       # 1~4단계. 덤프 303 MB 는 data/raw/ 에 한 번만 받는다
make ko KO_ARGS="--levels a1 --model sonnet --workers 4"   # 3단계만 다시
```

남은 재료는 소리 하나인데, 그 방법은 바로 앞 보고서가 이미 정했다. 노트북에서 Piper로 만들고, 앞 보고서가 잰 단어당 0.35초를 3,005개에 곱하면 18분이다. 그 전에 할 일은 A1 679줄을 읽는 30분이고, 그 30분만은 스크립트가 대신해 주지 않는다. ■

<details>
<summary>프로젝트 구조와 스크립트 전문 펼쳐 보기</summary>

```
construct_dataset/
├── Makefile                  # setup / wordlist / ipa / ko / merge / all
├── README.md
├── requirements.txt          # anthropic, pydantic — 3단계에서만 쓴다
├── .gitignore                # .venv/, data/raw/
├── third_party/
│   └── goethe-institute-wordlist/    # git 서브모듈. a1/ a2/ b1/ 아래 알파벳별 TSV
├── scripts/
│   ├── common.py             # 경로와 TSV·JSONL 입출력
│   ├── 01_wordlist.py        # TSV → wordlist.jsonl
│   ├── 02_ipa.py             # 덤프 → kaikki_matches.jsonl, ipa.jsonl
│   ├── 03_ko.py              # 언어 모델 → ko_draft.tsv
│   └── 04_merge.py           # → words.json, review_queue.tsv, stats.json
├── data/
│   ├── raw/
│   │   └── raw-wiktextract-data.jsonl.gz   # kaikki.org, 303 MB, git 제외
│   ├── wordlist.jsonl        # 1단계. 3,005줄
│   ├── kaikki_matches.jsonl  # 2단계 중간. 덤프에서 건진 3,684줄의 축약본
│   ├── ipa.jsonl             # 2단계. id → IPA, 관사, 복수형, 커먼즈 mp3 URL
│   ├── ko_draft.tsv          # 3단계. 모델 초안
│   ├── overrides.tsv         # 사람이 고친 것. 어느 열이든 채우면 이긴다
│   ├── words.json            # 4단계. 앱이 읽는 파일
│   ├── review_queue.tsv      # 4단계. 사람이 볼 항목과 이유
│   └── stats.json            # 4단계. 등급별 개수
└── tts_poc/                  # 앞 보고서의 오디오 실험
```

### Makefile

```make
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
```

### scripts/common.py

```python
"""네 단계 스크립트가 공유하는 경로와 입출력 도우미.

모든 경로는 construct_dataset/ 를 기준으로 잡는다. 어느 디렉터리에서 실행해도 같은 파일을 본다.
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent  # construct_dataset/
DATA = ROOT / "data"
RAW = DATA / "raw"  # git 제외. 300 MB짜리 위키낱말사전 덤프가 여기 온다.
WORDLIST_REPO = ROOT / "third_party" / "goethe-institute-wordlist"

LEVELS = ("a1", "a2", "b1")
OVERRIDE_FIELDS = ["id", "de", "article", "plural", "ipa", "ko", "note"]

# 단계별 산출물. 앞 단계의 출력이 뒷 단계의 입력이다.
WORDLIST = DATA / "wordlist.jsonl"          # 1단계: 표제어·관사·복수형·등급·예문
KAIKKI_GZ = RAW / "raw-wiktextract-data.jsonl.gz"
KAIKKI_MATCHES = DATA / "kaikki_matches.jsonl"  # 2단계 중간: 덤프에서 건진 원본 항목(축약)
IPA = DATA / "ipa.jsonl"                    # 2단계: id → IPA
KO_DRAFT = DATA / "ko_draft.tsv"            # 3단계: 언어 모델이 쓴 한국어 뜻 초안
OVERRIDES = DATA / "overrides.tsv"          # 사람이 고친 것. 관사·복수형·IPA·뜻 어느 열이든 채우면 그것이 이긴다.
WORDS = DATA / "words.json"                 # 4단계: 앱이 읽는 최종 파일
REVIEW = DATA / "review_queue.tsv"          # 4단계: 사람이 봐야 할 항목 목록


def log(*args: object) -> None:
    print(*args, file=sys.stderr, flush=True)


def read_jsonl(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def write_jsonl(path: Path, rows) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
            n += 1
    return n


def read_tsv(path: Path) -> list[dict]:
    """헤더가 있는 TSV. '#'으로 시작하는 줄과 빈 줄은 건너뛴다. 없으면 빈 목록."""
    if not path.exists():
        return []
    with path.open(encoding="utf-8", newline="") as f:
        lines = [ln for ln in f if ln.strip() and not ln.startswith("#")]
    if not lines:
        return []
    reader = csv.DictReader(lines, delimiter="\t", quoting=csv.QUOTE_NONE)
    return [dict(r) for r in reader]


def write_tsv(path: Path, rows: list[dict], fields: list[str], header_comment: str = "") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        if header_comment:
            for line in header_comment.strip().splitlines():
                f.write(f"# {line}\n")
        w = csv.DictWriter(f, fieldnames=fields, delimiter="\t", quoting=csv.QUOTE_NONE,
                           escapechar="\\", extrasaction="ignore", lineterminator="\n")
        w.writeheader()
        for r in rows:
            w.writerow({k: ("" if r.get(k) is None else str(r.get(k)).replace("\t", " ").replace("\n", " "))
                        for k in fields})
```

### scripts/01_wordlist.py

```python
"""1단계: 괴테 Wortliste TSV → data/wordlist.jsonl

입력  third_party/goethe-institute-wordlist/{a1,a2,b1}/[a-z].tsv
      열은 셋이다. 표제어 \t 독일어 예문 \t 영어 번역. (b1의 일부 파일에만 헤더 줄이 있다.)
      표제어에는 관사·복수형 힌트·동사 변화형·뜻 번호가 한 문자열에 섞여 있다.
        der Vater, -ä          die Adresse,-en        das Buch, -ü, er(1)
        der Apfel, ¨-          abholen(2)             (sich) vorstellen
        sein, ist, war, ist gewesen                   gut, besser, am besten
출력  표제어 하나에 한 줄. 같은 표제어의 뜻 번호 (1)(2)…는 예문만 모아서 하나로 합친다.
      두 등급에 모두 나오는 단어는 낮은 등급 하나로 합치고 levels 에 둘 다 적는다.

실행  python scripts/01_wordlist.py [--levels a1,a2,b1]
"""
from __future__ import annotations

import argparse
import re
import unicodedata
from collections import OrderedDict

from common import LEVELS, WORDLIST, WORDLIST_REPO, log, write_jsonl

ARTICLES = ("der", "die", "das")
SENSE_RE = re.compile(r"\s*\((\d+)\)\s*$")                     # abholen(2)
NUMBER_RE = re.compile(r"\s*\((Sg|Pl)\.?\)", re.I)             # Achtung (Sg.)  die Eltern (Pl.)
REGION_RE = re.compile(r"\s*\((?:D|A|CH)(?:\s*,\s*(?:D|A|CH))*\)")  # (D, CH)
TWO_NOUNS_RE = re.compile(r"^(der|die|das)\s+(.+?)\s*/\s*(der|die|das)\s+(.+)$")  # die Ehefrau, -en/der Ehemann, -ä, er
# 복수형 힌트. ¨ 는 움라우트, -ä/-ö/-ü 도 움라우트, 그 뒤가 어미.  -n  -e  ¨-e  -¨e  ¨  -ä, er  -
PLURAL_RE = re.compile(r"^(?:(?P<uml>¨)\s*-?|-\s*(?P<uml2>¨)?)\s*(?P<vow>[äöüÄÖÜ])?(?:\s*,\s*)?(?P<suf>[a-zäöüß]*)$")
FULL_PLURAL_RE = re.compile(r"^[A-ZÄÖÜ][a-zäöüß]+$")           # das Studium, Studien
DROP_PAREN_RE = re.compile(r"\((?:sich(?: etwas)?|etwas|jemanden|jemandem|ein)\)\s*")

DROPPED: list[str] = []   # 예문 없는 조각 줄. 실행 끝에 찍어 준다.
UMLAUT = {"a": "ä", "o": "ö", "u": "ü", "A": "Ä", "O": "Ö", "U": "Ü"}


def umlaut(stem: str) -> str | None:
    """마지막 a/o/u/au 에 움라우트를 찍는다. Vater→Väter, Baum→Bäum(e), Bahnhof→Bahnhöf(e)."""
    for i in range(len(stem) - 1, -1, -1):
        ch = stem[i]
        if ch == "u" and i > 0 and stem[i - 1] in "aA":
            return stem[: i - 1] + UMLAUT[stem[i - 1]] + "u" + stem[i + 1:]
        if ch in UMLAUT:
            return stem[:i] + UMLAUT[ch] + stem[i + 1:]
    return None


def expand_plural(lemma: str, hint: str) -> str | None:
    """'-ä, e' 같은 힌트를 실제 복수형으로 편다. 못 풀면 None.

    '-s/-n' 처럼 둘을 적어 둔 것은 앞의 것을, '¨- → Kiste' 같은 참조 표시는 떼고 본다.
    """
    hint = re.sub(r"\s*(→|->).*$", "", hint)
    hint = hint.replace("–", "-").replace("—", "-").strip()

    def build(m: "re.Match[str]") -> str | None:
        stem = lemma
        if m.group("uml") or m.group("uml2") or m.group("vow"):
            stem = umlaut(lemma)
            if stem is None:
                return None
        return join_suffix(stem, m.group("suf"))

    for part in re.split(r"\s*/\s*", hint):
        part = part.strip()
        if not part:
            continue
        m = PLURAL_RE.match(part)
        if m:
            return build(m)
        first = part.split(",")[0].strip()          # 'der Ski, -, -er' → '-'
        m = PLURAL_RE.match(first)
        if m:
            return build(m)
        if FULL_PLURAL_RE.match(part):
            return part
        return None
    return None


def join_suffix(stem: str, suf: str) -> str:
    """어미를 붙인다. 목록은 -e 로 끝나는 말에도 '-en' 이라 적고, 라틴어계 어미는 갈아 끼워야 한다.

    Adresse+en → Adressen   Datum+en → Daten   Praktikum+a → Praktika
    Thema+en → Themen       Konto+en → Konten  Praxis+en → Praxen     Bäum+e → Bäume (aum 은 라틴어 어미가 아니다)
    """
    if not suf:
        return stem
    if stem.endswith("um") and not stem.endswith(("aum", "äum")) and (suf.startswith("e") or suf == "a"):
        return stem[:-2] + suf
    if stem.endswith(("a", "o")) and suf == "en":
        return stem[:-1] + suf
    if stem.endswith("is") and suf == "en":
        return stem[:-2] + suf
    if stem.endswith("e") and suf.startswith("e"):
        return stem + suf[1:]
    return stem + suf


def clean_lemma(text: str) -> str:
    """'(sich) vorstellen'→'vorstellen', '(ab)fahren'→'abfahren', '(Kredit)-Karte'→'Kreditkarte', E-Mail 은 그대로."""
    text = DROP_PAREN_RE.sub("", text)
    text = re.sub(r"\(([^)]{2,}?)-\)", r"(\1)", text)    # (Back-)Ofen: 괄호에 붙은 하이픈은 합성어 표시일 뿐
    text = re.sub(r"\(([^)]{2,}?)\)-", r"(\1)", text)    # (Kredit)-Karte.  (E-)Mail 의 한 글자 접두는 하이픈을 남긴다
    had_paren = "(" in text
    text = text.replace("(", "").replace(")", "")
    if had_paren:                                      # (Back-)Ofen → BackOfen → Backofen
        text = re.sub(r"(?<=[a-zäöüß])([A-ZÄÖÜ])(?=[a-zäöüß])", lambda m: m.group(1).lower(), text)
    return re.sub(r"\s+", " ", text).strip(" -")


def lookup_keys(lemma_part: str) -> list[str]:
    """위키낱말사전 대조에 쓸 후보를 우선순위대로. 앞의 것이 먼저 시도된다."""
    keys: list[str] = []

    def add(k: str) -> None:
        k = re.sub(r"\s+", " ", k).strip(" -")
        if k and k not in keys:
            keys.append(k)

    for alt in lemma_part.split("/"):
        add(clean_lemma(alt))
        add(re.sub(r"\([^)]*\)", "", alt))          # 괄호 안을 통째로 버린 꼴: (ab)fahren → fahren
        add(re.sub(r"\([^)]*\)", "", alt).replace("sich ", ""))
    return keys


def slugify(text: str) -> str:
    text = text.translate(str.maketrans({"ä": "ae", "ö": "oe", "ü": "ue", "Ä": "ae", "Ö": "oe", "Ü": "ue", "ß": "ss"}))
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-") or "x"


def parse_headword(raw: str) -> list[dict]:
    """표제어 문자열 하나를 항목 dict 로. 드물게 두 표제어가 한 칸에 있어 list 를 돌려준다."""
    raw = raw.strip()
    m = SENSE_RE.search(raw)
    sense = int(m.group(1)) if m else None
    raw = SENSE_RE.sub("", raw)

    m2 = TWO_NOUNS_RE.match(raw)
    if m2:
        a, b = f"{m2.group(1)} {m2.group(2)}", f"{m2.group(3)} {m2.group(4)}"
        return [dict(e, sense=sense) for e in parse_headword(a) + parse_headword(b)]

    number = None
    if NUMBER_RE.search(raw):
        number = NUMBER_RE.search(raw).group(1).lower()
        raw = NUMBER_RE.sub("", raw)
    raw = REGION_RE.sub("", raw).strip()
    raw = re.sub(r"\s*(→|->).*$", "", raw)      # 'der Stock → D, CH: Etage' 같은 지역어 참조

    article = None
    body = raw
    m3 = re.match(r"^(der|die|das)\s+(.+)$", raw)
    if m3:
        article, body = m3.group(1), m3.group(2)

    lemma_part, _, hint = body.partition(",")
    lemma_part, hint = lemma_part.strip(), hint.strip()

    entry = {
        "de": (f"{article} {lemma_part}" if article else lemma_part),
        "lemma": clean_lemma(lemma_part.split("/")[0]),
        "article": article,
        "plural": None,
        "plural_hint": None,
        "forms": None,
        "number": number,
        "lookup_keys": lookup_keys(lemma_part),
        "sense": sense,
    }
    if article:
        entry["plural_hint"] = hint or None
        if hint:
            entry["plural"] = expand_plural(entry["lemma"], hint)
        elif number == "sg":
            entry["plural"] = None
    else:
        entry["forms"] = hint or None      # 동사 변화형이나 비교급이 여기 들어온다
    return [entry]


def read_level(level: str) -> list[tuple[dict, str, str]]:
    rows = []
    for path in sorted((WORDLIST_REPO / level).glob("[a-z].tsv")):
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip() or line.startswith("german word"):
                continue
            cols = line.split("\t")
            head, ex_de, ex_en = (cols + ["", ""])[:3]
            if not ex_de.strip():
                # PDF 를 옮기다 동사 변화형이 다음 줄로 넘어간 조각이다. "hat gechattet" 같은 것.
                DROPPED.append(f"{level}: {head.strip()}")
                continue
            for entry in parse_headword(head):
                rows.append((entry, ex_de.strip(), ex_en.strip()))
    return rows


def build(levels: list[str]) -> list[dict]:
    merged: "OrderedDict[tuple, dict]" = OrderedDict()
    for level in levels:
        for entry, ex_de, ex_en in read_level(level):
            key = (entry["lemma"].lower(), entry["article"])
            cur = merged.get(key)
            if cur is None:
                cur = dict(entry, level=level, levels=[level], examples=[])
                cur.pop("sense", None)
                merged[key] = cur
            else:
                # 같은 단어가 다시 나오면 빠진 정보만 채운다. 첫 등장(낮은 등급)의 표기가 이긴다.
                for k in ("plural", "plural_hint", "forms"):
                    if cur.get(k) is None and entry.get(k) is not None:
                        cur[k] = entry[k]
                for k in entry["lookup_keys"]:
                    if k not in cur["lookup_keys"]:
                        cur["lookup_keys"].append(k)
                if level not in cur["levels"]:
                    cur["levels"].append(level)
            if ex_de and not any(e["de"] == ex_de for e in cur["examples"]):
                cur["examples"].append({"de": ex_de, "en": ex_en, "level": level})

    # id: 등급이 아니라 단어에서 만든다. 등급이 바뀌어도 id 는 그대로여야 학습 기록이 살아남는다.
    seen: dict[str, int] = {}
    out = []
    for cur in merged.values():
        base = slugify(cur["lemma"])
        n = seen.get(base, 0) + 1
        seen[base] = n
        cur["id"] = base if n == 1 else f"{base}-{n}"
        out.append({k: cur[k] for k in ("id", "de", "lemma", "article", "plural", "plural_hint",
                                        "forms", "number", "level", "levels", "lookup_keys", "examples")})
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--levels", default=",".join(LEVELS), help="쉼표로 구분. 기본 a1,a2,b1")
    args = ap.parse_args()
    levels = [l.strip().lower() for l in args.levels.split(",") if l.strip()]
    if not (WORDLIST_REPO / "a1").exists():
        raise SystemExit(f"서브모듈이 비어 있다: git submodule update --init {WORDLIST_REPO.relative_to(WORDLIST_REPO.parent.parent)}")
    rows = build(levels)
    n = write_jsonl(WORDLIST, rows)
    by_level = {l: sum(1 for r in rows if r["level"] == l) for l in levels}
    nouns = sum(1 for r in rows if r["article"])
    with_plural = sum(1 for r in rows if r["plural"])
    unparsed = [r for r in rows if r["article"] and r["plural_hint"] and not r["plural"]]
    log(f"wordlist: {n} entries → {WORDLIST}")
    log(f"  by first level: {by_level}")
    log(f"  nouns {nouns}, plural expanded {with_plural}, plural hint unparsed {len(unparsed)}")
    for r in unparsed[:15]:
        log(f"    ? {r['de']}, {r['plural_hint']}")
    log(f"  dropped {len(DROPPED)} rows without an example sentence: {DROPPED}")


if __name__ == "__main__":
    main()
```

### scripts/02_ipa.py

```python
"""2단계: kaikki.org 독일어판 위키낱말사전 추출본에서 IPA 를 뽑는다.

입력  data/wordlist.jsonl                       (1단계 출력)
      data/raw/raw-wiktextract-data.jsonl.gz   (kaikki.org, 압축 303 MB, 풀면 2.8 GB — 풀지 않고 흘려 읽는다)
출력  data/kaikki_matches.jsonl   표제어와 겹치는 원본 항목만 축약해 둔 것. 덤프를 다시 안 받아도 되게.
      data/ipa.jsonl              id → ipa. 위키낱말사전이 아는 관사·복수형·Commons 녹음 URL 도 같이.

덤프 한 줄은 (표제어, 품사) 하나의 JSON 이다. 같은 철자가 여러 줄일 수 있다.
  sein   → 동사 / 소유대명사        Väter → 명사이지만 tags 에 form-of (변화형 페이지)
그래서 줄마다 점수를 매겨 하나를 고른다. 변화형 페이지는 감점, 관사가 있는 단어는 명사 우대.

실행  python scripts/02_ipa.py            # 덤프를 훑고(1~2분) 선택까지
      python scripts/02_ipa.py --reuse    # 덤프는 안 훑고 kaikki_matches.jsonl 에서 선택만 다시
"""
from __future__ import annotations

import argparse
import gzip
import json
import re
import time
from collections import defaultdict

from common import IPA, KAIKKI_GZ, KAIKKI_MATCHES, WORDLIST, log, read_jsonl, write_jsonl

WORD_RE = re.compile(r'"word":\s*"((?:[^"\\]|\\.)*)"')
GENDER_TO_ARTICLE = {"masculine": "der", "feminine": "die", "neuter": "das"}


def slim(rec: dict) -> dict:
    """한 줄 JSON 에서 우리가 쓸 것만 남긴다. 원본은 뜻풀이·어원·번역까지 있어 줄당 수 KB 다."""
    ipa = [s["ipa"] for s in rec.get("sounds", []) if s.get("ipa")]
    audio = [s["mp3_url"] for s in rec.get("sounds", []) if s.get("mp3_url")]
    plural, articles = [], []
    for f in rec.get("forms", []):
        tags = f.get("tags", [])
        if tags == ["nominative", "plural"] and f.get("form") and f["form"] not in plural:
            plural.append(f["form"])
        if tags == ["nominative", "singular"] and f.get("article") and f["article"] not in articles:
            articles.append(f["article"])     # der Beamte / die Beamte 처럼 둘일 수 있다
    if not articles:
        articles = [GENDER_TO_ARTICLE[t] for t in rec.get("tags", []) if t in GENDER_TO_ARTICLE]
    glosses = []
    for s in rec.get("senses", [])[:3]:
        g = s.get("glosses") or s.get("raw_glosses") or []
        if g:
            glosses.append(g[0][:120])
    return {
        "word": rec["word"],
        "pos": rec.get("pos"),
        "pos_title": rec.get("pos_title"),
        "tags": rec.get("tags", []),
        "ipa": ipa,
        "audio": audio,
        "articles": articles,
        "plurals": plural,
        "n_senses": len(rec.get("senses", [])),
        "glosses": glosses,
    }


def stream_matches(gz_path, wanted: set[str]):
    """덤프를 한 줄씩 흘려 읽으며 표제어가 wanted 에 있는 줄만 JSON 으로 푼다.

    2.8 GB 를 전부 json.loads 하면 몇 분이 걸린다. 줄 머리의 "word" 값만 정규식으로 먼저 보고,
    걸린 줄만 제대로 판다. 대부분의 줄은 첫 400자 안에 word 가 있다.
    """
    t0 = time.time()
    n_lines = n_hit = 0
    with gzip.open(gz_path, "rt", encoding="utf-8") as f:
        for line in f:
            n_lines += 1
            m = WORD_RE.search(line, 0, 400) or WORD_RE.search(line)
            if not m:
                continue
            w = m.group(1)
            if "\\" in w:
                w = json.loads(f'"{w}"')
            if w not in wanted:
                continue
            rec = json.loads(line)
            if rec.get("lang_code") != "de":
                continue
            n_hit += 1
            yield slim(rec)
            if n_lines % 200000 == 0:
                log(f"  … {n_lines:,} lines, {n_hit} matches, {time.time() - t0:.0f}s")
    log(f"  scanned {n_lines:,} lines in {time.time() - t0:.0f}s, {n_hit} German entries matched")


def clean_ipa(s: str) -> str | None:
    s = s.strip().strip("[]/").strip()
    if not s or "…" in s or "..." in s:
        return None
    return s


def score(entry: dict, rec: dict, key_rank: int) -> int:
    s = 0
    if "form-of" in rec["tags"]:
        s -= 100                     # Väter, möchten(변화형) 같은 페이지
    if any(clean_ipa(x) for x in rec["ipa"]):
        s += 20
    if entry["article"]:
        s += 10 if rec["pos"] == "noun" else 0
        if entry["article"] in rec["articles"]:
            s += 5
    elif rec["pos"] == "noun":
        s -= 2                       # 관사 없는 표제어가 명사 페이지와 겹치면 (Achtung) 약간만 밀어 둔다
    s += min(rec["n_senses"], 5)
    s -= 10 * key_rank               # lookup_keys 앞쪽 후보가 우선. Fahrrad/Rad 에서 Fahrrad 가 이겨야 한다
    return s


def choose(entry: dict, by_word: dict[str, list[dict]]) -> dict:
    cands = []
    for rank, key in enumerate(entry["lookup_keys"]):
        for rec in by_word.get(key, []):
            cands.append((score(entry, rec, rank), rec))
    if not cands:
        return {"id": entry["id"], "ipa": None, "matched_word": None}
    cands.sort(key=lambda t: -t[0])
    best = cands[0][1]
    ipas = []
    for _, rec in cands:
        for x in rec["ipa"]:
            c = clean_ipa(x)
            if c and c not in ipas:
                ipas.append(c)
    primary = next((clean_ipa(x) for x in best["ipa"] if clean_ipa(x)), None) or (ipas[0] if ipas else None)
    return {
        "id": entry["id"],
        "ipa": primary,
        "ipa_alts": [x for x in ipas if x != primary],
        "matched_word": best["word"],
        "pos": best["pos"],
        "pos_title": best["pos_title"],
        "wikt_articles": best["articles"],
        "wikt_plurals": best["plurals"],
        "audio": best["audio"],
        "glosses": best["glosses"],
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--reuse", action="store_true", help="덤프를 다시 훑지 않고 kaikki_matches.jsonl 을 쓴다")
    args = ap.parse_args()

    entries = read_jsonl(WORDLIST)
    wanted = {k for e in entries for k in e["lookup_keys"]}
    log(f"ipa: {len(entries)} entries, {len(wanted)} lookup keys")

    if args.reuse and KAIKKI_MATCHES.exists():
        matches = read_jsonl(KAIKKI_MATCHES)
        log(f"  reusing {len(matches)} cached matches from {KAIKKI_MATCHES}")
    else:
        if not KAIKKI_GZ.exists():
            raise SystemExit(f"덤프가 없다: make {KAIKKI_GZ.relative_to(KAIKKI_GZ.parents[2])}  (kaikki.org, 303 MB)")
        matches = list(stream_matches(KAIKKI_GZ, wanted))
        write_jsonl(KAIKKI_MATCHES, matches)

    by_word: dict[str, list[dict]] = defaultdict(list)
    for m in matches:
        by_word[m["word"]].append(m)

    rows = [choose(e, by_word) for e in entries]
    write_jsonl(IPA, rows)
    have = sum(1 for r in rows if r["ipa"])
    by_level = defaultdict(lambda: [0, 0])
    for e, r in zip(entries, rows):
        by_level[e["level"]][1] += 1
        by_level[e["level"]][0] += bool(r["ipa"])
    log(f"  IPA found for {have}/{len(rows)} → {IPA}")
    for lvl, (h, t) in sorted(by_level.items()):
        log(f"    {lvl}: {h}/{t} ({100 * h / t:.1f}%)")
    missing = [e["de"] for e, r in zip(entries, rows) if not r["ipa"]]
    log(f"  no IPA (first 20): {missing[:20]}")


if __name__ == "__main__":
    main()
```

### scripts/03_ko.py

```python
"""3단계: 언어 모델이 한국어 뜻 초안을 쓴다. 검수는 사람이 overrides.tsv 에서 한다.

입력  data/wordlist.jsonl   (1단계)  표제어·등급·예문
      data/ipa.jsonl        (2단계, 있으면)  위키낱말사전 품사를 힌트로 같이 보낸다
출력  data/ko_draft.tsv     id, de, level, ko, note, model  — 모델 초안. 다시 돌리면 이미 있는 id 는 건너뛴다.
      data/overrides.tsv    사람이 고친 것. ko 열을 채우면 4단계에서 초안보다 우선한다. (관사·복수형·IPA 도 같은 파일)

백엔드
  sdk   Anthropic Python SDK.  ANTHROPIC_API_KEY (또는 ANTHROPIC_AUTH_TOKEN) 이 있을 때. 기본 모델 claude-opus-5.
  cli   로컬 Claude Code (`claude -p`). API 키 없이 구독으로 돌릴 때. 모델은 Claude Code 기본값.
  auto  키가 있으면 sdk, 없으면 cli.  (기본)

한 요청에 CHUNK 개 항목을 JSON 으로 보내고, 같은 개수의 {id, ko, note} 를 JSON 스키마로 강제해 받는다.
답에서 빠진 id 는 모아서 한 번 더 묻는다. 그래도 없으면 비워 두고 4단계의 검수 목록에 오른다.

실행  python scripts/03_ko.py                          # 전체, auto 백엔드
      python scripts/03_ko.py --levels a1 --workers 4
      python scripts/03_ko.py --backend sdk --model claude-opus-5
      python scripts/03_ko.py --dry-run                # 첫 묶음의 프롬프트만 찍는다
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

from pydantic import BaseModel

from common import IPA, KO_DRAFT, OVERRIDES, OVERRIDE_FIELDS, LEVELS, WORDLIST, log, read_jsonl, read_tsv

CHUNK = 60
SDK_MODEL = "claude-opus-5"
DRAFT_FIELDS = ["id", "de", "level", "ko", "note", "model"]

SYSTEM = """\
너는 독일어-한국어 학습용 단어장의 편집자다. 괴테 인스티투트 A1~B1 단어 목록의 항목을 JSON으로 받아
각 항목에 한국어 뜻(ko)과 짧은 메모(note)를 단다.

ko 규칙
- 사전 표제어처럼 짧게. 문장이나 설명이 아니라 뜻만. 흔한 뜻 1~3개를 쉼표로 구분한다.
  예: "아버지" / "데리러 가다, 찾아오다" / "오래된, 늙은"
- 예문에 쓰인 뜻을 반드시 넣고, 예문이 여러 개면 그 뜻들을 앞에 둔다.
- 명사는 명사형, 동사는 '-다' 기본형, 형용사는 '-한/-ㄴ' 꼴, 부사·전치사·접속사는 기능이 드러나는
  우리말("~부터", "그러나", "아마도").
- 독일어 단어, 관사, 복수형, 괄호 설명은 ko에 쓰지 않는다.

note 규칙
- 학습자가 꼭 알아야 할 것만 20자 이내. 예: "재귀동사", "복수형만 씀", "분리동사", "구어",
  "예문은 관용구", "장소 이동은 4격". 없으면 빈 문자열.

출력은 스키마대로 JSON만. id는 입력 그대로 돌려주고, 항목을 빼거나 더하지 않는다."""

SCHEMA = {
    "type": "object",
    "properties": {
        "items": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"id": {"type": "string"}, "ko": {"type": "string"}, "note": {"type": "string"}},
                "required": ["id", "ko", "note"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["items"],
    "additionalProperties": False,
}


class KoItem(BaseModel):
    id: str
    ko: str
    note: str = ""


class KoBatch(BaseModel):
    items: list[KoItem]


def build_prompt(entries: list[dict], pos_hint: dict[str, str]) -> str:
    items = []
    for e in entries:
        item = {"id": e["id"], "de": e["de"], "level": e["level"].upper()}
        if e.get("forms"):
            item["forms"] = e["forms"]
        if pos_hint.get(e["id"]):
            item["pos"] = pos_hint[e["id"]]
        item["examples"] = [{"de": x["de"], "en": x["en"]} for x in e["examples"][:4]]
        items.append(item)
    return f"다음 {len(items)}개 항목의 ko와 note를 써라.\n" + json.dumps(items, ensure_ascii=False, indent=1)


# ---- 백엔드 두 가지 -------------------------------------------------------------------

def call_sdk(prompt: str, model: str) -> tuple[KoBatch, str]:
    import anthropic

    client = anthropic.Anthropic()          # ANTHROPIC_API_KEY 를 읽는다
    resp = client.messages.parse(
        model=model,
        max_tokens=16000,
        system=SYSTEM,
        messages=[{"role": "user", "content": prompt}],
        output_format=KoBatch,
    )
    if resp.stop_reason == "refusal":
        raise RuntimeError(f"model refused: {resp.stop_details}")
    if resp.parsed_output is None:
        raise RuntimeError(f"no parsed output (stop_reason={resp.stop_reason})")
    return resp.parsed_output, resp.model


def call_cli(prompt: str, model: str | None) -> tuple[KoBatch, str]:
    cmd = ["claude", "-p", "--no-session-persistence", "--tools", "",
           "--system-prompt", SYSTEM, "--output-format", "json", "--json-schema", json.dumps(SCHEMA)]
    if model:
        cmd += ["--model", model]
    cmd.append(prompt)
    env = {k: v for k, v in os.environ.items() if k != "CLAUDECODE"}   # 세션 안에서 돌려도 되게
    proc = subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=900)
    if proc.returncode != 0:
        raise RuntimeError(f"claude exit {proc.returncode}: {proc.stderr.strip()[:400]}")
    data = json.loads(proc.stdout)
    if data.get("is_error") or data.get("structured_output") is None:
        raise RuntimeError(f"claude error: {str(data.get('result'))[:400]}")
    used = [m for m in data.get("modelUsage", {}) if not m.startswith("claude-haiku")]   # haiku 는 보조 호출
    return KoBatch.model_validate(data["structured_output"]), (used[0] if used else (model or "claude-code-default"))


def pick_backend(name: str) -> str:
    if name != "auto":
        return name
    if os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN"):
        return "sdk"
    if shutil.which("claude"):
        return "cli"
    raise SystemExit("ANTHROPIC_API_KEY 도 없고 claude CLI 도 없다. 둘 중 하나가 필요하다.")


# ---- 묶음 처리 --------------------------------------------------------------------------

def run_chunk(chunk: list[dict], pos_hint: dict[str, str], backend: str, model: str | None) -> tuple[list[KoItem], list[dict], str]:
    """한 묶음을 보내고 (받은 항목, 빠진 항목, 실제 쓰인 모델) 을 돌려준다."""
    prompt = build_prompt(chunk, pos_hint)
    batch, used = call_sdk(prompt, model or SDK_MODEL) if backend == "sdk" else call_cli(prompt, model)
    wanted = {e["id"]: e for e in chunk}
    got = [it for it in batch.items if it.id in wanted and it.ko.strip()]
    got_ids = {it.id for it in got}
    missing = [e for e in chunk if e["id"] not in got_ids]
    return got, missing, used


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--levels", default=",".join(LEVELS))
    ap.add_argument("--backend", choices=["auto", "sdk", "cli"], default="auto")
    ap.add_argument("--model", default=None, help="sdk 기본 claude-opus-5, cli 기본은 Claude Code 설정값")
    ap.add_argument("--workers", type=int, default=2, help="동시에 보낼 요청 수")
    ap.add_argument("--chunk", type=int, default=CHUNK)
    ap.add_argument("--limit", type=int, default=None, help="처음 N 항목만 (시험용)")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    levels = {l.strip().lower() for l in args.levels.split(",")}
    entries = [e for e in read_jsonl(WORDLIST) if e["level"] in levels]
    done = {r["id"] for r in read_tsv(KO_DRAFT)}
    todo = [e for e in entries if e["id"] not in done]
    if args.limit:
        todo = todo[: args.limit]
    pos_hint = {r["id"]: r["pos_title"] for r in read_jsonl(IPA) if r.get("pos_title")} if IPA.exists() else {}
    chunks = [todo[i:i + args.chunk] for i in range(0, len(todo), args.chunk)]
    log(f"ko: {len(entries)} entries in {sorted(levels)}, {len(done)} already drafted, {len(todo)} to do in {len(chunks)} chunks")

    if args.dry_run:
        if chunks:
            print(build_prompt(chunks[0], pos_hint))
        return
    if not chunks:
        return

    backend = pick_backend(args.backend)
    model_label = args.model or (SDK_MODEL if backend == "sdk" else "claude-code-default")
    log(f"  backend={backend} model={model_label} workers={args.workers}")

    if not OVERRIDES.exists():
        OVERRIDES.write_text(
            "# 사람이 고친 것. 4단계에서 자동 생성값보다 우선한다. 빈 칸은 무시. de 는 참고용.\n"
            "# plural 은 관사 없이 (Väter), ipa 는 대괄호 없이 (ˈfaːtɐ).\n"
            + "\t".join(OVERRIDE_FIELDS) + "\n", encoding="utf-8")

    lock = threading.Lock()
    new_file = not KO_DRAFT.exists()
    fh = KO_DRAFT.open("a", encoding="utf-8")
    if new_file:
        fh.write("\t".join(DRAFT_FIELDS) + "\n")
    by_id = {e["id"]: e for e in todo}

    def save(items: list[KoItem], used: str) -> None:
        with lock:
            for it in items:
                e = by_id[it.id]
                row = [it.id, e["de"], e["level"], it.ko.strip(), it.note.strip(), used]
                fh.write("\t".join(c.replace("\t", " ").replace("\n", " ") for c in row) + "\n")
            fh.flush()

    def work(chunk: list[dict]) -> list[dict]:
        got, missing, used = run_chunk(chunk, pos_hint, backend, args.model)
        save(got, used)
        return missing

    leftovers: list[dict] = []
    n_ok = n_fail = 0
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(work, c): i for i, c in enumerate(chunks)}
        for fut in as_completed(futures):
            i = futures[fut]
            try:
                missing = fut.result()
                leftovers += missing
                n_ok += 1
                log(f"  chunk {i + 1}/{len(chunks)} ok" + (f", {len(missing)} missing" if missing else ""))
            except Exception as exc:  # noqa: BLE001 — 한 묶음 실패가 전체를 멈추면 안 된다. 다시 돌리면 이어서 한다.
                n_fail += 1
                log(f"  chunk {i + 1}/{len(chunks)} FAILED: {exc}")

    if leftovers:
        log(f"  retrying {len(leftovers)} missing ids once")
        for i in range(0, len(leftovers), args.chunk):
            try:
                got, still, used = run_chunk(leftovers[i:i + args.chunk], pos_hint, backend, args.model)
                save(got, used)
                if still:
                    log(f"    still missing: {[e['id'] for e in still]}")
            except Exception as exc:  # noqa: BLE001
                log(f"    retry FAILED: {exc}")
    fh.close()
    log(f"ko: chunks ok {n_ok}, failed {n_fail} → {KO_DRAFT}")


if __name__ == "__main__":
    main()
```

### scripts/04_merge.py

```python
"""4단계: 1~3단계 산출물을 하나로 합쳐 앱이 읽을 words.json 을 만든다.

입력  data/wordlist.jsonl   data/ipa.jsonl   data/ko_draft.tsv   data/overrides.tsv
출력  data/words.json        항목 하나는 이런 모양이다.
        {"id": "vater", "de": "der Vater", "lemma": "Vater", "article": "der", "plural": "die Väter",
         "level": "A1", "ipa": "ˈfaːtɐ", "ko": "아버지", "note": "", "pos": "Substantiv",
         "examples": [{"de": "Mein Vater ist Arbeiter.", "en": "My father is a worker."}]}
      data/review_queue.tsv  사람이 봐야 할 항목. 이유 열에 no_ipa / no_ko / plural_mismatch / article_mismatch.
                             고칠 것은 data/overrides.tsv 에 적는다. 열 하나만 채워도 된다.
      data/stats.json        등급별 개수와 커버리지. 보고서용.

복수형은 괴테 목록의 힌트를 편 것을 쓰고, 힌트가 없거나 못 푼 것은 위키낱말사전 것을 쓴다.
둘 다 있는데 다르면 검수 목록에 올린다. 어느 쪽이 맞는지는 사람이 본다.

실행  python scripts/04_merge.py
"""
from __future__ import annotations

import json
from collections import Counter, defaultdict

import re

from common import IPA, KO_DRAFT, OVERRIDES, REVIEW, WORDLIST, WORDS, DATA, log, read_jsonl, read_tsv, write_tsv


def main() -> None:
    entries = read_jsonl(WORDLIST)
    ipa = {r["id"]: r for r in read_jsonl(IPA)} if IPA.exists() else {}
    draft = {r["id"]: r for r in read_tsv(KO_DRAFT)}
    overrides = {r["id"]: {k: v.strip() for k, v in r.items() if k != "id" and v and v.strip()}
                 for r in read_tsv(OVERRIDES)}

    words, review = [], []
    stats = defaultdict(Counter)
    for e in entries:
        lvl = e["level"]
        stats[lvl]["entries"] += 1
        p = ipa.get(e["id"], {})
        ov = overrides.get(e["id"], {})
        ko_row = draft.get(e["id"]) or {}
        reasons = []
        plural_only = e.get("number") == "pl"            # die Geschwister (Pl.): 관사 die 는 복수 관사다

        article = ov.get("article") or e["article"]
        de = re.sub(r"^(der|die|das) ", article + " ", e["de"]) if ov.get("article") else e["de"]
        plural = ov.get("plural") or e["plural"]
        wikt_plurals = p.get("wikt_plurals") or []
        wikt_articles = p.get("wikt_articles") or []
        if plural_only:
            plural = None
        elif plural is None and wikt_plurals:
            plural = wikt_plurals[0]
            stats[lvl]["plural_from_wikt"] += 1
        elif plural and wikt_plurals and not ov.get("plural") and plural not in wikt_plurals \
                and not (plural.endswith("n") and plural[:-1] in wikt_plurals):   # die Beamten / Beamte 는 같은 말
            reasons.append(f"plural_mismatch goethe={plural} wikt={'/'.join(wikt_plurals)}")
            stats[lvl]["plural_mismatch"] += 1
        if article and wikt_articles and not plural_only and not ov.get("article") and article not in wikt_articles:
            reasons.append(f"article_mismatch goethe={article} wikt={'/'.join(wikt_articles)}")
            stats[lvl]["article_mismatch"] += 1

        ipa_val = ov.get("ipa") or p.get("ipa")
        if ipa_val:
            stats[lvl]["ipa"] += 1
        else:
            reasons.append("no_ipa")
        ko = ov.get("ko") or ko_row.get("ko")
        note = ov.get("note") if "note" in ov else ko_row.get("note", "")
        if ko:
            stats[lvl]["ko"] += 1
        else:
            reasons.append("no_ko")
        for k in ov:
            if k != "de":
                stats[lvl][f"override_{k}"] += 1

        words.append({
            "id": e["id"],
            "de": de,
            "lemma": e["lemma"],
            "article": article,
            "plural": (f"die {plural}" if plural else None),
            "level": lvl.upper(),
            "ipa": ipa_val,
            "ko": ko or None,
            "note": note or "",
            "pos": p.get("pos_title"),
            "examples": [{"de": x["de"], "en": x["en"]} for x in e["examples"]],
        })
        if reasons:
            review.append({"id": e["id"], "de": de, "level": lvl, "ipa": ipa_val or "",
                           "ko": ko or "", "reasons": "; ".join(reasons)})

    WORDS.write_text(json.dumps(words, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    write_tsv(REVIEW, review, ["id", "de", "level", "ipa", "ko", "reasons"],
              "사람이 봐야 할 항목. 고칠 것은 overrides.tsv 에 같은 id 로 적는다. 다시 merge 하면 여기서 사라진다.")
    keys = sorted({k for c in stats.values() for k in c})
    total = {k: sum(c[k] for c in stats.values()) for k in keys}
    out = {"total": total, "by_level": {l: dict(c) for l, c in sorted(stats.items())}, "review_queue": len(review),
           "review_reasons": dict(Counter(r.split()[0] for row in review for r in row["reasons"].split("; ")))}
    (DATA / "stats.json").write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

    log(f"merge: {len(words)} words → {WORDS}")
    for l, c in sorted(stats.items()):
        n = c["entries"]
        log(f"  {l}: {n} entries, ipa {c['ipa']} ({100 * c['ipa'] / n:.1f}%), ko {c['ko']} ({100 * c['ko'] / n:.1f}%),"
            f" plural mismatch {c['plural_mismatch']}, article mismatch {c['article_mismatch']}")
    log(f"  review queue: {len(review)} → {REVIEW}   reasons: {out['review_reasons']}")


if __name__ == "__main__":
    main()
```

</details>

---

관련 문서
- [2026_09_09_20_28_german_phonics_app.md](2026_09_09_20_28_german_phonics_app.md) - 재료 다섯을 정리한 첫 보고서
- [2026_09_09_20_35_local_tts_beats_cloud.md](2026_09_09_20_35_local_tts_beats_cloud.md) - 다섯 번째 재료인 오디오

출처
- [ilkermeliksitki/goethe-institute-wordlist](https://github.com/ilkermeliksitki/goethe-institute-wordlist), 괴테 인스티투트 A1·A2·B1 Wortliste 의 TSV 사본. 라이선스 표기 없음
- [Goethe-Zertifikat A1 Wortliste (PDF)](https://www.goethe.de/pro/relaunch/prf/de/A1_SD1_Wortliste_02.pdf)
- [kaikki.org 독일어판 위키낱말사전 원본 추출 데이터](https://kaikki.org/dewiktionary/rawdata.html), CC BY-SA 4.0
- [tatuylonen/wiktextract](https://github.com/tatuylonen/wiktextract)
- [Claude Code CLI 레퍼런스](https://code.claude.com/docs/en/cli-reference), `--print`, `--json-schema`, `--system-prompt`, `--tools`
- [Anthropic Python SDK](https://github.com/anthropics/anthropic-sdk-python), `messages.parse` 와 구조화 출력
