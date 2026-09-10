<script lang="ts">
  import WordDetails from './WordDetails.svelte';
  import { EXAMPLES_AT_FIRST } from '../lib/constants';
  import type { Sentence, Settings, Word } from '../lib/types';

  interface Props {
    word?: Word;
    index: number;
    queueLength: number;
    doneToday: number;
    remaining: number;
    revealed: boolean;
    settings: Settings;
    sentences: Record<string, Sentence>;
    surfaces: Map<string, string>;
    playingId?: string;
    onReveal: () => void;
    onGrade: (ok: boolean) => void;
    onMore: () => void;
    onPlay: (id: string, button: HTMLButtonElement) => void;
  }

  let { word, index, queueLength, doneToday, remaining, revealed, settings, sentences, surfaces, playingId, onReveal, onGrade, onMore, onPlay }: Props = $props();
</script>

<section class="view">
  {#if word}
    <article class="card">
      <div class="card-head">
        <span class="pos">{word.pos || ''}</span>
        <span class="counter">{index + 1} / {queueLength}</span>
      </div>
      <button class="face" data-open={revealed ? '1' : '0'} onclick={onReveal}>
        <span class="lemma">{word.lemma}</span>
        {#if !revealed}<span class="face-hint">소리 내어 읽어 본 다음 눌러 보세요</span>{/if}
      </button>
      {#if revealed}
        <div class="back">
          <WordDetails {word} {sentences} {surfaces} {settings} {playingId} exampleLimit={EXAMPLES_AT_FIRST} {onPlay} />
        </div>
      {/if}
    </article>
    {#if revealed}
      <div class="grade">
        <button class="btn again" onclick={() => onGrade(false)}>아직이에요<kbd>1</kbd></button>
        <button class="btn good" onclick={() => onGrade(true)}>알아요<kbd>2</kbd></button>
      </div>
    {/if}
  {:else}
    <div class="done">
      <p class="done-title">오늘 몫을 끝냈습니다.</p>
      <p class="done-sub">이번에 {doneToday}개를 봤습니다. {remaining ? `아직 ${remaining}개가 남아 있습니다.` : '복습할 때가 된 단어가 더 없습니다.'}</p>
      {#if remaining}<button class="btn wide" onclick={onMore}>더 하기</button>{/if}
    </div>
  {/if}
  <p class="keys">데스크톱에서는 <kbd>Space</kbd> 확인 · <kbd>1</kbd> 아직 · <kbd>2</kbd> 알아요 · <kbd>P</kbd> 다시 듣기</p>
</section>
