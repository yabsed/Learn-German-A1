<script lang="ts">
  import Examples from './Examples.svelte';
  import type { Sentence, Settings, Word } from '../lib/types';

  interface Props {
    word: Word;
    sentences: Record<string, Sentence>;
    surfaces: Map<string, string>;
    wordById: Map<string, Word>;
    settings: Settings;
    playingId?: string;
    exampleLimit?: number;
    onPlay: (id: string, button: HTMLButtonElement) => void;
    onWord: (id: string) => void;
  }

  let { word, sentences, surfaces, wordById, settings, playingId, exampleLimit = 0, onPlay, onWord }: Props = $props();
  let plural = $derived(word.plural?.replace(/^(die|der|das) /, '') || '');
  let pluralArticle = $derived(word.plural?.match(/^(die|der|das) /)?.[1] || '');
</script>

{#if word.article || word.plural}
  <div class="full">
    {#if word.article}<em>{word.article}</em> {/if}{word.lemma}
    {#if word.plural} · 복수 {#if pluralArticle}<em>{pluralArticle}</em> {/if}{plural}{/if}
  </div>
{/if}
<div class="ipa-row">
  <span class="ipa">{word.ipa ? `[${word.ipa}]` : ''}</span>
  <button class:on={playingId === word.id} class="play" aria-pressed={playingId === word.id} onclick={(e) => onPlay(word.id, e.currentTarget)}><span class="tri">{playingId === word.id ? '❚❚' : '▶'}</span> {playingId === word.id ? '일시정지' : '듣기'}</button>
</div>
<p class="ko">{word.ko}</p>
{#if word.note}<p class="note">{word.note}</p>{/if}
<Examples ids={word.ex} {sentences} currentId={word.id} {surfaces} {wordById} {settings} {playingId} limit={exampleLimit} {onPlay} {onWord} />
