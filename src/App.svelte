<script lang="ts">
  import { onMount } from 'svelte';
  import Browse from './components/Browse.svelte';
  import Header from './components/Header.svelte';
  import Practice from './components/Practice.svelte';
  import Stats from './components/Stats.svelte';
  import WordSheet from './components/WordSheet.svelte';
  import { DEFAULT_SETTINGS, KEY_PROGRESS, KEY_SETTINGS, LEVEL } from './lib/constants';
  import { buildQueue, gradedCard } from './lib/scheduler';
  import { readStorage, writeStorage } from './lib/storage';
  import type { Dataset, Progress, Sentence, Settings, View, Word } from './lib/types';
  import { buildSurfaceIndex } from './lib/words';

  let words = $state<Word[]>([]);
  let sentences = $state<Record<string, Sentence>>({});
  let audioInfo = $state<Dataset['audio']>();
  let byId = $state(new Map<string, Word>());
  let surfaces = $state(new Map<string, string>());
  let progress = $state<Progress>(readStorage<Progress>(KEY_PROGRESS, {}));
  let settings = $state<Settings>({ ...DEFAULT_SETTINGS, ...readStorage<Partial<Settings>>(KEY_SETTINGS, {}) });
  let queue = $state<string[]>([]);
  let index = $state(0);
  let doneToday = $state(0);
  let revealed = $state(false);
  let view = $state<View>('practice');
  let sheetWord = $state<Word>();
  let loading = $state(true);
  let error = $state('');
  let player: HTMLAudioElement;
  let playingId = $state<string>();

  let currentWord = $derived(byId.get(queue[index]));
  let remaining = $derived(words.filter((word) => !progress[word.id] || progress[word.id].due <= Date.now()).length);
  let progressPercent = $derived(queue.length ? Math.round(index / queue.length * 100) : 0);
  const contentBase = import.meta.env.DEV
    ? `${import.meta.env.BASE_URL}app/`
    : import.meta.env.BASE_URL;

  function startSession() {
    queue = buildQueue(words, progress, settings.session);
    index = 0;
    revealed = false;
  }

  function saveProgress() {
    writeStorage(KEY_PROGRESS, progress);
  }

  function grade(ok: boolean) {
    const id = queue[index];
    if (!id) return;
    progress = { ...progress, [id]: gradedCard(progress[id], ok) };
    saveProgress();
    if (!ok && queue.length - index > 1) {
      const nextQueue = [...queue];
      nextQueue.splice(Math.min(index + 4, nextQueue.length), 0, id);
      queue = nextQueue;
    }
    doneToday += 1;
    index += 1;
    revealed = false;
  }

  function play(id: string, _button: HTMLButtonElement) {
    if (playingId === id && !player.paused) {
      player.pause();
      return;
    }
    if (!player.paused) player.pause();
    player.src = `${contentBase}audio/${id}.mp3`;
    playingId = id;
    player.play()
      .catch(() => {
        if (playingId === id) stopPlaying();
      });
  }

  function stopPlaying() {
    playingId = undefined;
  }

  function pauseAudio() {
    if (!player.paused) player.pause();
    stopPlaying();
  }

  function navigate(next: View) {
    location.hash = `#/${next}`;
  }

  function openWord(id: string) {
    // Opening a definition is navigation, never an audio trigger. It also
    // prevents an already-playing card/example from following the user into
    // the new sheet.
    pauseAudio();
    location.hash = `#/word/${id}`;
  }

  function closeSheet() {
    pauseAudio();
    if (location.hash.startsWith('#/word/')) history.back();
    else sheetWord = undefined;
  }

  function applyRoute() {
    const parts = location.hash.replace(/^#\/?/, '').split('/');
    if (parts[0] === 'word' && byId.has(parts[1])) {
      sheetWord = byId.get(parts[1]);
      return;
    }
    if (sheetWord) pauseAudio();
    sheetWord = undefined;
    if (parts[0] === 'practice' || parts[0] === 'browse' || parts[0] === 'stats') {
      if (view !== parts[0]) window.scrollTo(0, 0);
      view = parts[0];
    } else {
      view = 'practice';
    }
  }

  function updateSettings(next: Settings) {
    settings = next;
    writeStorage(KEY_SETTINGS, settings);
  }

  function resetProgress() {
    if (!confirm('익힌 기록을 모두 지웁니다. 되돌릴 수 없습니다.')) return;
    progress = {};
    saveProgress();
    doneToday = 0;
    startSession();
  }

  function handleKeydown(event: KeyboardEvent) {
    if ((event.target as HTMLElement).matches('input, select, textarea')) return;
    if (sheetWord) {
      if (event.key === 'Escape') closeSheet();
      return;
    }
    if (view !== 'practice') return;
    if (event.key === ' ' || event.key === 'Enter') {
      event.preventDefault();
      if (!revealed) {
        revealed = true;
        if (settings.autoplay && currentWord) {
          const button = document.querySelector<HTMLButtonElement>('.card .play');
          if (button) play(currentWord.id, button);
        }
      }
    } else if (event.key === '1' && revealed) grade(false);
    else if (event.key === '2' && revealed) grade(true);
    else if (event.key.toLowerCase() === 'p' && currentWord) {
      const button = document.querySelector<HTMLButtonElement>('.card .play');
      if (button) play(currentWord.id, button);
    }
  }

  function reveal() {
    if (!currentWord) return;
    if (revealed) {
      const button = document.querySelector<HTMLButtonElement>('.card .play');
      if (button) play(currentWord.id, button);
      return;
    }
    revealed = true;
    if (settings.autoplay) {
      requestAnimationFrame(() => {
        const button = document.querySelector<HTMLButtonElement>('.card .play');
        if (button) play(currentWord!.id, button);
      });
    }
  }

  onMount(() => {
    async function load() {
      try {
        const response = await fetch(`${contentBase}data/${LEVEL}.json`);
        if (!response.ok) throw new Error(String(response.status));
        const data = await response.json() as Dataset;
        words = data.words;
        sentences = data.sentences;
        audioInfo = data.audio;
        byId = new Map(words.map((word) => [word.id, word]));
        surfaces = buildSurfaceIndex(words);
        startSession();

        if (location.hash.startsWith('#/word/')) {
          const target = location.hash;
          history.replaceState(null, '', '#/browse');
          view = 'browse';
          history.pushState(null, '', target);
        }
        applyRoute();
        window.addEventListener('hashchange', applyRoute);
        window.addEventListener('keydown', handleKeydown);

        if (!import.meta.env.DEV && 'serviceWorker' in navigator && location.protocol !== 'file:') {
          navigator.serviceWorker.register(`${import.meta.env.BASE_URL}sw.js`).catch(() => undefined);
        }
      } catch {
        error = '단어 파일을 읽지 못했습니다. npm run dev로 띄워 주세요.';
      } finally {
        loading = false;
      }
    }
    void load();
    return () => {
      window.removeEventListener('hashchange', applyRoute);
      window.removeEventListener('keydown', handleKeydown);
    };
  });
</script>

<Header {view} {settings} {progressPercent} practiceFinished={!currentWord} onNavigate={navigate} onSettingsChange={updateSettings} />

<main>
  {#if loading}<p class="loading">단어를 불러오는 중…</p>
  {:else if error}<p class="loading">{error}</p>
  {:else if view === 'practice'}
    <Practice word={currentWord} {index} queueLength={queue.length} {doneToday} {remaining} {revealed} {settings} {sentences} {surfaces} {playingId} onReveal={reveal} onGrade={grade} onMore={startSession} onPlay={play} />
  {:else if view === 'browse'}
    <Browse {words} {progress} onWord={openWord} />
  {:else}
    <Stats {words} {sentences} {progress} audio={audioInfo} onReset={resetProgress} />
  {/if}
</main>

{#if sheetWord}
  <WordSheet word={sheetWord} {sentences} {surfaces} {settings} {playingId} onClose={closeSheet} onPlay={play} />
{/if}

<audio bind:this={player} preload="none" onended={stopPlaying} onpause={stopPlaying} onerror={stopPlaying}></audio>
