<script lang="ts">
  import { glossParts, sentenceParts } from '../lib/words';
  import type { Sentence, Settings, Word } from '../lib/types';

  interface Props {
    ids: string[];
    sentences: Record<string, Sentence>;
    currentId: string;
    surfaces: Map<string, string>;
    wordById: Map<string, Word>;
    settings: Settings;
    playingId?: string;
    limit?: number;
    onPlay: (id: string, button: HTMLButtonElement) => void;
    onWord: (id: string) => void;
  }

  let { ids, sentences, currentId, surfaces, wordById, settings, playingId, limit = 0, onPlay, onWord }: Props = $props();
  let expanded = $state(false);
  let revealedMeanings = $state(new Set<string>());
  let shown = $derived(expanded || !limit ? ids : ids.slice(0, limit));

  $effect(() => {
    currentId;
    expanded = false;
    revealedMeanings = new Set();
  });

  function openLinkedWord(event: MouseEvent, id: string) {
    event.preventDefault();
    onWord(id);
  }

  function revealMeaning(id: string) {
    revealedMeanings = new Set([...revealedMeanings, id]);
  }
</script>

<div class="examples">
  {#each shown as id (id)}
    {@const sentence = sentences[id]}
    {#if sentence}
      {@const gloss = glossParts(sentence.de, sentence.g, currentId, surfaces)}
      {@const veiled = settings.hideKorean && !revealedMeanings.has(id)}
      <div class="ex">
        <button class:on={playingId === id} class="ex-play" type="button" aria-label={playingId === id ? '예문 일시정지' : '예문 듣기'} aria-pressed={playingId === id} onclick={(e) => onPlay(id, e.currentTarget)}>{playingId === id ? '❚❚' : '▶'}</button>
        <div>
          {#if gloss.length}
            <div class="ex-gloss-line">
              {#each gloss as group}
                <span class="ex-gloss-pair">
                  <span class="ex-gloss-de">
                    {#each group.parts as part}
                      {#if part.current}<span class="ex-here">{part.text}</span>
                      {:else if part.wordId && wordById.get(part.wordId)}
                        {@const target = wordById.get(part.wordId)!}
                        <a
                          class="ex-link"
                          href={`#/word/${target.id}`}
                          aria-label={`${part.text}: ${target.ko}. 상세 보기`}
                          onclick={(event) => openLinkedWord(event, target.id)}
                        >{part.text}</a>
                      {:else}{part.text}{/if}
                    {/each}
                  </span>
                  <span class:veiled class="ex-gloss-ko" aria-hidden={veiled || undefined}>{group.ko}</span>
                </span>
              {/each}
            </div>
          {:else}
            <div class="ex-de">
              {#each sentenceParts(sentence.de, currentId, surfaces) as part}
                {#if part.current}<span class="ex-here">{part.text}</span>
                {:else if part.wordId && wordById.get(part.wordId)}
                  {@const target = wordById.get(part.wordId)!}
                  <a
                    class="ex-link"
                    href={`#/word/${target.id}`}
                    aria-label={`${part.text}: ${target.ko}. 상세 보기`}
                    onclick={(event) => openLinkedWord(event, target.id)}
                  >{part.text}</a>
                {:else}{part.text}{/if}
              {/each}
            </div>
          {/if}
          {#if veiled}
            <button class="ex-reveal" type="button" onclick={() => revealMeaning(id)}>예문 풀이 보기</button>
          {:else}
            <div class="ex-ko">{sentence.ko}</div>
          {/if}
          {#if settings.english && sentence.en}<div class="ex-en">{sentence.en}</div>{/if}
        </div>
      </div>
    {/if}
  {/each}
</div>
{#if limit && ids.length > limit && !expanded}
  <button class="more" onclick={() => expanded = true}>예문 더 보기</button>
{/if}
