<script lang="ts">
  import { sentenceParts } from '../lib/words';
  import type { Sentence, Settings } from '../lib/types';

  interface Props {
    ids: string[];
    sentences: Record<string, Sentence>;
    currentId: string;
    surfaces: Map<string, string>;
    settings: Settings;
    limit?: number;
    onPlay: (id: string, button: HTMLButtonElement) => void;
    onWord: (id: string) => void;
  }

  let { ids, sentences, currentId, surfaces, settings, limit = 0, onPlay, onWord }: Props = $props();
  let expanded = $state(false);
  let shown = $derived(expanded || !limit ? ids : ids.slice(0, limit));

  $effect(() => {
    currentId;
    expanded = false;
  });
</script>

<div class="examples">
  {#each shown as id (id)}
    {@const sentence = sentences[id]}
    {#if sentence}
      <div class="ex">
        <button class="ex-play" type="button" aria-label="예문 듣기" onclick={(e) => onPlay(id, e.currentTarget)}>▶</button>
        <div>
          <div class="ex-de">
            {#each sentenceParts(sentence.de, currentId, surfaces) as part}
              {#if part.current}<span class="ex-here">{part.text}</span>
              {:else if part.wordId}<a class="ex-link" href={`#/word/${part.wordId}`} onclick={(e) => { e.preventDefault(); onWord(part.wordId!); }}>{part.text}</a>
              {:else}{part.text}{/if}
            {/each}
          </div>
          <button class:veiled={settings.hideKorean} class="ex-ko" type="button" onclick={(e) => e.currentTarget.classList.remove('veiled')}>{sentence.ko}</button>
          {#if settings.english && sentence.en}<div class="ex-en">{sentence.en}</div>{/if}
        </div>
      </div>
    {/if}
  {/each}
</div>
{#if limit && ids.length > limit && !expanded}
  <button class="more" onclick={() => expanded = true}>예문 더 보기</button>
{/if}
