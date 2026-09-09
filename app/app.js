/* 독일어 A1 발음 연습.
 *
 * 서버가 없다. 단어와 예문은 data/a1.json 한 파일에서 오고, 소리는
 * audio/{id}.mp3 정적 파일이며, 무엇을 익혔는지는 localStorage 에만 남는다.
 * 파일 이름은 데이터셋이 정한 id 를 그대로 쓴다. 여기서 다시 만들지 않는다. */

'use strict';

const LEVEL = 'a1';
const DAY = 86400000;

// 라이트너 상자. 맞히면 한 칸 오르고, 그 칸의 날수만큼 뒤에 다시 나온다.
const INTERVALS = [0, 1, 3, 7, 16, 35];
const TOP_BOX = INTERVALS.length - 1;

const KEY_PROGRESS = 'lgv.progress.' + LEVEL;
const KEY_SETTINGS = 'lgv.settings';

const EXAMPLES_AT_FIRST = 3;

const $ = (id) => document.getElementById(id);

const store = {
  read(key, fallback) {
    try { return JSON.parse(localStorage.getItem(key)) ?? fallback; }
    catch { return fallback; }
  },
  write(key, value) {
    try { localStorage.setItem(key, JSON.stringify(value)); } catch { /* 사파리 비공개 모드 */ }
  },
};

const app = {
  words: [], byId: new Map(), sentences: {},
  progress: store.read(KEY_PROGRESS, {}),
  settings: Object.assign(
    { autoplay: true, english: false, hideKorean: false, session: 20 },
    store.read(KEY_SETTINGS, {})
  ),
  queue: [], at: 0, doneToday: 0, showAllExamples: false,
  view: 'practice',
};

const save = () => store.write(KEY_PROGRESS, app.progress);
const saveSettings = () => store.write(KEY_SETTINGS, app.settings);

/* ── 예정 ─────────────────────────────────────────────────────────── */

const card = (id) => app.progress[id] || { box: 0, due: 0, seen: 0, ok: 0 };
const isNew = (id) => !app.progress[id];
const isDue = (id) => { const c = app.progress[id]; return !c || c.due <= Date.now(); };

/** 복습할 때가 된 것을 먼저, 그다음 아직 안 본 것을 순서대로. */
function buildQueue() {
  const now = Date.now();
  const due = [], fresh = [];
  for (const w of app.words) {
    const c = app.progress[w.id];
    if (!c) fresh.push(w.id);
    else if (c.due <= now) due.push(w.id);
  }
  due.sort((a, b) => app.progress[a].due - app.progress[b].due);
  const size = app.settings.session;
  const all = due.concat(fresh);
  app.queue = size > 0 ? all.slice(0, size) : all;
  app.at = 0;
}

function grade(ok) {
  const id = app.queue[app.at];
  if (!id) return;
  const c = Object.assign({ box: 0, due: 0, seen: 0, ok: 0 }, app.progress[id]);
  c.seen += 1;
  if (ok) { c.ok += 1; c.box = Math.min(c.box + 1, TOP_BOX); }
  else { c.box = c.box > 1 ? 1 : 0; }
  c.due = ok ? Date.now() + INTERVALS[c.box] * DAY : Date.now();
  app.progress[id] = c;
  save();

  // 틀린 것은 이번 세션 안에서 다시 만난다.
  if (!ok && app.queue.length - app.at > 1) {
    app.queue.splice(Math.min(app.at + 4, app.queue.length), 0, id);
  }
  app.doneToday += 1;
  app.at += 1;
  renderCard();
}

/* ── 소리 ─────────────────────────────────────────────────────────── */

const player = $('player');
let playingBtn = null;

function play(id, button) {
  if (playingBtn) playingBtn.classList.remove('on');
  playingBtn = button || null;
  if (playingBtn) playingBtn.classList.add('on');
  player.src = `audio/${id}.mp3`;
  player.play().catch(() => { /* 자동 재생 차단, 사용자가 다시 누르면 된다 */ });
}
player.addEventListener('ended', () => { if (playingBtn) playingBtn.classList.remove('on'); playingBtn = null; });
player.addEventListener('error', () => { if (playingBtn) playingBtn.classList.remove('on'); playingBtn = null; });

/* ── 카드 ─────────────────────────────────────────────────────────── */

const esc = (text) => String(text).replace(/[&<>"]/g, (ch) =>
  ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[ch]));

/** "der Vater · 복수 die Väter". 관사만 색을 달리해 보여 준다.
 *  plural 에는 이미 die 가 붙어 있으므로 여기서 또 붙이지 않는다. */
function fullForm(w) {
  // 관사도 복수형도 없으면 표제어를 그대로 되풀이할 뿐이라 아무것도 내놓지 않는다.
  if (!w.article && !w.plural) return '';
  const parts = [w.article ? `<em>${esc(w.article)}</em> ${esc(w.lemma)}` : esc(w.lemma)];
  if (w.plural) {
    parts.push('복수 ' + esc(w.plural).replace(/^(die|der|das) /, '<em>$1</em> '));
  }
  return parts.join(' · ');
}

function exampleNode(sid, sentence) {
  const row = document.createElement('div');
  row.className = 'ex';

  const btn = document.createElement('button');
  btn.className = 'ex-play';
  btn.type = 'button';
  btn.textContent = '▶';
  btn.setAttribute('aria-label', '예문 듣기');
  btn.addEventListener('click', () => play(sid, btn));

  const body = document.createElement('div');
  const de = document.createElement('div');
  de.className = 'ex-de';
  de.textContent = sentence.de;
  body.append(de);

  const ko = document.createElement('div');
  ko.className = 'ex-ko' + (app.settings.hideKorean ? ' veiled' : '');
  ko.textContent = sentence.ko;
  if (app.settings.hideKorean) {
    ko.addEventListener('click', () => ko.classList.remove('veiled'), { once: true });
  }
  body.append(ko);

  if (app.settings.english && sentence.en) {
    const en = document.createElement('div');
    en.className = 'ex-en';
    en.textContent = sentence.en;
    body.append(en);
  }

  row.append(btn, body);
  return row;
}

function fillExamples(container, ids, limit, moreBtn) {
  container.textContent = '';
  const shown = limit ? ids.slice(0, limit) : ids;
  for (const sid of shown) {
    const sentence = app.sentences[sid];
    if (sentence) container.append(exampleNode(sid, sentence));
  }
  if (moreBtn) moreBtn.hidden = !limit || ids.length <= limit;
}

function renderCard() {
  const id = app.queue[app.at];
  const finished = !id;
  $('card').hidden = finished;
  $('grade').hidden = true;
  $('done').hidden = !finished;
  $('daybar').hidden = finished;

  if (finished) {
    const left = app.words.filter((w) => isNew(w.id) || isDue(w.id)).length;
    $('done-sub').textContent = left
      ? `이번에 ${app.doneToday}개를 봤습니다. 아직 ${left}개가 남아 있습니다.`
      : `이번에 ${app.doneToday}개를 봤습니다. 복습할 때가 된 단어가 더 없습니다.`;
      $('btn-more-session').hidden = left === 0;
    return;
  }

  const w = app.byId.get(id);
  app.showAllExamples = false;

  $('card-pos').textContent = w.pos || '';
  $('card-counter').textContent = `${app.at + 1} / ${app.queue.length}`;
  $('card-lemma').textContent = w.lemma;
  $('card-full').innerHTML = fullForm(w);
  $('card-ipa').textContent = w.ipa ? `[${w.ipa}]` : '';
  $('card-ko').textContent = w.ko;
  $('card-note').textContent = w.note || '';
  $('card-note').hidden = !w.note;

  $('back').hidden = true;
  $('face').dataset.open = '0';

  const bar = $('daybar-fill');
  bar.style.width = `${Math.round((app.at / app.queue.length) * 100)}%`;
}

function reveal() {
  if ($('card').hidden || !$('back').hidden) return;
  const w = app.byId.get(app.queue[app.at]);
  if (!w) return;
  $('back').hidden = false;
  $('face').dataset.open = '1';
  $('grade').hidden = false;
  fillExamples($('examples'), w.ex, EXAMPLES_AT_FIRST, $('more-examples'));
  if (app.settings.autoplay) play(w.id, $('play-word'));
}

/* ── 단어장 ───────────────────────────────────────────────────────── */

let filter = 'all';

/** 한글 자판으로는 ä ö ü ß 를 치기 어렵다. backerei 로도 Bäckerei 가 걸리게 접는다.
 *  검색어는 반드시 한 벌로 접는다. 두 벌로 접으면 자기 자신이 부분 문자열이 아니게 된다. */
function fold(text, spell) {
  const map = spell ? { ä: 'ae', ö: 'oe', ü: 'ue' } : { ä: 'a', ö: 'o', ü: 'u' };
  return text.toLowerCase()
    .replace(/[äöü]/g, (c) => map[c])
    .replace(/ß/g, 'ss')
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '');
}

/** 찾을 쪽만 두 벌로 둔다. Bäckerei 로 쳐도 backerei 로 쳐도 baeckerei 로 쳐도 걸린다.
 *  단어마다 한 번만 접는다. 679개를 글자마다 접으면 입력이 버벅인다. */
function haystack(w) {
  if (w._hay === undefined) {
    const raw = [w.de, w.lemma, w.ko, w.note || ''].join(' ');
    const bare = fold(raw, false);
    const spelled = fold(raw, true);
    w._hay = bare + (spelled === bare ? '' : ' ' + spelled);
  }
  return w._hay;
}

function matches(w, needle) {
  if (!needle) return true;
  return haystack(w).includes(needle);
}

function passesFilter(w) {
  const c = app.progress[w.id];
  if (filter === 'new') return !c;
  if (filter === 'learning') return !!c && c.box < TOP_BOX;
  if (filter === 'known') return !!c && c.box >= TOP_BOX;
  return true;
}

function renderList() {
  const needle = fold($('search').value.trim(), false);
  const found = app.words.filter((w) => passesFilter(w) && matches(w, needle));
  $('browse-count').textContent = `${found.length}개`;

  const list = $('list');
  list.textContent = '';
  const frag = document.createDocumentFragment();
  for (const w of found) {
    const li = document.createElement('li');
    const row = document.createElement('button');
    row.className = 'row';
    row.type = 'button';

    const left = document.createElement('div');
    const de = document.createElement('div');
    de.className = 'row-de';
    de.textContent = w.de;
    const ko = document.createElement('div');
    ko.className = 'row-ko';
    ko.textContent = w.ko;
    left.append(de, ko);

    const dot = document.createElement('span');
    dot.className = 'dot';
    dot.dataset.box = String(card(w.id).box);

    row.append(left, dot);
    row.addEventListener('click', () => openSheet(w));
    li.append(row);
    frag.append(li);
  }
  list.append(frag);
}

/* ── 상세 시트 ────────────────────────────────────────────────────── */

function openSheet(w) {
  const body = $('sheet-body');
  body.textContent = '';

  const lemma = document.createElement('div');
  lemma.className = 'lemma';
  lemma.style.textAlign = 'left';
  lemma.style.fontSize = '38px';
  lemma.textContent = w.lemma;

  const full = document.createElement('div');
  full.className = 'full';
  full.innerHTML = fullForm(w);

  const row = document.createElement('div');
  row.className = 'ipa-row';
  const ipa = document.createElement('span');
  ipa.className = 'ipa';
  ipa.textContent = w.ipa ? `[${w.ipa}]` : '';
  const playBtn = document.createElement('button');
  playBtn.className = 'play';
  playBtn.type = 'button';
  playBtn.innerHTML = '<span class="tri">▶</span> 듣기';
  playBtn.addEventListener('click', () => play(w.id, playBtn));
  row.append(ipa, playBtn);

  const ko = document.createElement('p');
  ko.className = 'ko';
  ko.textContent = w.ko;

  body.append(lemma, full, row, ko);

  if (w.note) {
    const note = document.createElement('p');
    note.className = 'note';
    note.textContent = w.note;
    body.append(note);
  }

  const examples = document.createElement('div');
  examples.className = 'examples';
  fillExamples(examples, w.ex, 0, null);
  body.append(examples);

  $('sheet-wrap').hidden = false;
  play(w.id, playBtn);
}

function closeSheet() { $('sheet-wrap').hidden = true; }

/* ── 진도 ─────────────────────────────────────────────────────────── */

function renderStats() {
  const total = app.words.length;
  let seen = 0, known = 0, dueNow = 0;
  const boxes = new Array(INTERVALS.length).fill(0);
  for (const w of app.words) {
    const c = app.progress[w.id];
    if (!c) continue;
    seen += 1;
    boxes[c.box] += 1;
    if (c.box >= TOP_BOX) known += 1;
    if (c.due <= Date.now()) dueNow += 1;
  }
  const tiles = [
    [seen, `본 단어 / ${total}`],
    [known, '익힘'],
    [dueNow + (total - seen), '오늘 볼 것'],
  ];
  $('tiles').innerHTML = tiles
    .map(([n, label]) => `<div class="tile"><b>${n}</b><span>${label}</span></div>`)
    .join('');

  const names = ['처음', '1일 뒤', '3일 뒤', '1주 뒤', '2주 뒤', '한 달 뒤'];
  const peak = Math.max(1, ...boxes);
  $('bars').innerHTML = boxes
    .map((n, i) => `<div class="bar"><span>${names[i]}</span>
      <div class="bar-track"><div class="bar-fill" style="width:${(n / peak) * 100}%"></div></div>
      <b>${n}</b></div>`)
    .join('');
}

/* ── 화면 전환 ────────────────────────────────────────────────────── */

function show(view) {
  app.view = view;
  for (const tab of document.querySelectorAll('.tab')) {
    tab.setAttribute('aria-selected', String(tab.dataset.view === view));
  }
  $('view-practice').hidden = view !== 'practice';
  $('view-browse').hidden = view !== 'browse';
  $('view-stats').hidden = view !== 'stats';
  if (view === 'browse') renderList();
  if (view === 'stats') renderStats();
  window.scrollTo(0, 0);
}

/* ── 오프라인 저장 ────────────────────────────────────────────────── */

async function downloadAll() {
  const button = $('btn-offline');
  const status = $('offline-status');
  if (!('caches' in window)) { status.textContent = '이 브라우저는 오프라인 저장을 지원하지 않습니다.'; return; }

  const urls = app.words.map((w) => `audio/${w.id}.mp3`)
    .concat(Object.keys(app.sentences).map((sid) => `audio/${sid}.mp3`));
  const cache = await caches.open('lgv-audio-v1');
  button.disabled = true;

  let done = 0, failed = 0;
  const queue = urls.slice();
  const worker = async () => {
    for (let url = queue.pop(); url; url = queue.pop()) {
      if (!(await cache.match(url))) {
        try { await cache.add(url); } catch { failed += 1; }
      }
      done += 1;
      if (done % 25 === 0 || done === urls.length) {
        status.textContent = `${done} / ${urls.length}개 저장했습니다.`;
      }
    }
  };
  await Promise.all([worker(), worker(), worker(), worker()]);

  button.disabled = false;
  status.textContent = failed
    ? `${urls.length - failed}개를 저장했습니다. ${failed}개는 받지 못했습니다.`
    : `${urls.length}개를 모두 저장했습니다. 이제 인터넷 없이도 됩니다.`;
}

/* ── 이어 붙이기 ──────────────────────────────────────────────────── */

function wireUp() {
  $('face').addEventListener('click', () => {
    if ($('back').hidden) reveal();
    else play(app.queue[app.at], $('play-word'));
  });
  $('play-word').addEventListener('click', (e) => { e.stopPropagation(); play(app.queue[app.at], $('play-word')); });
  $('btn-again').addEventListener('click', () => grade(false));
  $('btn-good').addEventListener('click', () => grade(true));
  $('btn-more-session').addEventListener('click', () => { buildQueue(); renderCard(); });

  $('more-examples').addEventListener('click', () => {
    const w = app.byId.get(app.queue[app.at]);
    fillExamples($('examples'), w.ex, 0, $('more-examples'));
  });

  for (const tab of document.querySelectorAll('.tab')) {
    tab.addEventListener('click', () => show(tab.dataset.view));
  }

  $('settings-btn').addEventListener('click', () => {
    const panel = $('settings-panel');
    panel.hidden = !panel.hidden;
    $('settings-btn').setAttribute('aria-expanded', String(!panel.hidden));
  });

  const bind = (id, key, fromEl, toEl) => {
    const el = $(id);
    toEl(el, app.settings[key]);
    el.addEventListener('change', () => { app.settings[key] = fromEl(el); saveSettings(); });
  };
  bind('opt-autoplay', 'autoplay', (el) => el.checked, (el, v) => { el.checked = v; });
  bind('opt-english', 'english', (el) => el.checked, (el, v) => { el.checked = v; });
  bind('opt-hidekorean', 'hideKorean', (el) => el.checked, (el, v) => { el.checked = v; });
  bind('opt-session', 'session', (el) => Number(el.value), (el, v) => { el.value = String(v); });

  $('search').addEventListener('input', renderList);
  for (const chip of document.querySelectorAll('.chip')) {
    chip.addEventListener('click', () => {
      filter = chip.dataset.filter;
      document.querySelectorAll('.chip').forEach((c) => c.classList.toggle('on', c === chip));
      renderList();
    });
  }

  $('sheet-close').addEventListener('click', closeSheet);
  $('sheet-wrap').addEventListener('click', (e) => { if (e.target === $('sheet-wrap')) closeSheet(); });

  $('btn-offline').addEventListener('click', downloadAll);
  $('btn-reset').addEventListener('click', () => {
    if (!confirm('익힌 기록을 모두 지웁니다. 되돌릴 수 없습니다.')) return;
    app.progress = {};
    save();
    app.doneToday = 0;
    buildQueue();
    renderCard();
    renderStats();
  });

  document.addEventListener('keydown', (e) => {
    if (e.target.matches('input, select, textarea')) return;
    if (!$('sheet-wrap').hidden) { if (e.key === 'Escape') closeSheet(); return; }
    if (app.view !== 'practice') return;
    if (e.key === ' ' || e.key === 'Enter') { e.preventDefault(); reveal(); }
    else if (e.key === '1') { if (!$('grade').hidden) grade(false); }
    else if (e.key === '2') { if (!$('grade').hidden) grade(true); }
    else if (e.key.toLowerCase() === 'p') { play(app.queue[app.at], $('play-word')); }
  });
}

async function start() {
  try {
    const response = await fetch(`data/${LEVEL}.json`);
    if (!response.ok) throw new Error(response.status);
    const data = await response.json();
    app.words = data.words;
    app.sentences = data.sentences;
    app.byId = new Map(app.words.map((w) => [w.id, w]));
  } catch (err) {
    $('loading').textContent = '단어 파일을 읽지 못했습니다. 로컬 파일을 그냥 연 것이라면 make serve 로 띄워 주세요.';
    return;
  }
  $('loading').hidden = true;
  wireUp();
  buildQueue();
  renderCard();

  if ('serviceWorker' in navigator && location.protocol !== 'file:') {
    navigator.serviceWorker.register('sw.js').catch(() => { /* 없어도 앱은 돈다 */ });
  }
}

start();
