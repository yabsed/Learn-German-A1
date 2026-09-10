<script lang="ts">
  import { TOP_BOX } from '../lib/constants';
  import { matchesWord, passesFilter } from '../lib/search';
  import type { Progress, Word, WordFilter } from '../lib/types';

  interface Props {
    words: Word[];
    progress: Progress;
    onWord: (id: string) => void;
  }

  let { words, progress, onWord }: Props = $props();
  let query = $state('');
  let filter = $state<WordFilter>('all');
  let found = $derived(words.filter((word) => passesFilter(word, filter, progress, TOP_BOX) && matchesWord(word, query)));

  const filters: Array<[WordFilter, string]> = [
    ['all', '전체'], ['new', '안 본 것'], ['learning', '익히는 중'], ['known', '익힘'],
  ];
</script>

<section class="view">
  <div class="search-row">
    <input type="search" bind:value={query} placeholder="단어나 뜻으로 찾기" autocomplete="off" enterkeyhint="search" aria-label="단어나 뜻으로 찾기">
  </div>
  <div class="chips">
    {#each filters as item}
      <button class:active={filter === item[0]} class="chip" onclick={() => filter = item[0]}>{item[1]}</button>
    {/each}
  </div>
  <p class="hint">{found.length}개</p>
  <ul class="list">
    {#each found as word (word.id)}
      <li>
        <button class="row" onclick={() => onWord(word.id)}>
          <span><span class="row-de">{word.de}</span><span class="row-ko">{word.ko}</span></span>
          <span class="dot" data-box={progress[word.id]?.box ?? 0}></span>
        </button>
      </li>
    {/each}
  </ul>
</section>
