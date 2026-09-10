<script lang="ts">
  import { onMount } from 'svelte';
  import { renderMarkdown } from '../lib/markdown';

  const files = import.meta.glob('../../construct_dataset/third_party/German-A1-Notes/Lektion*.md', {
    query: '?raw',
    import: 'default',
  }) as Record<string, () => Promise<string>>;

  const lessons = Object.entries(files)
    .map(([path, load]) => ({
      number: Number(path.match(/Lektion(\d+)\.md$/)?.[1]),
      load,
    }))
    .sort((a, b) => a.number - b.number);

  let selected = $state(0);
  let expanded = $state(false);
  let text = $state('');
  let lesson = $derived(lessons[selected]);
  let title = $derived(text.match(/^#\s+(.+)$/m)?.[1] ?? `Lektion ${String(lesson.number).padStart(2, '0')}`);
  let document = $derived(renderMarkdown(text));

  async function loadLesson(index: number) {
    text = '';
    const next = await lessons[index].load();
    if (index === selected) text = next;
  }

  function choose(index: number) {
    selected = index;
    expanded = false;
    window.scrollTo(0, 0);
    void loadLesson(index);
  }

  onMount(() => void loadLesson(selected));
</script>

<section class="notes-view">
  <div class="notes-intro">
    <p class="eyebrow">German A1 Notes</p>
    <h2>해설서</h2>
    <p>13개 레슨의 원문 노트를 읽을 수 있습니다.</p>
  </div>

  <div class="lesson-picker" class:expanded>
    <button class="lesson-current" aria-expanded={expanded} onclick={() => expanded = !expanded}>
      <span><small>Lektion {String(lesson.number).padStart(2, '0')}</small>{title}</span>
      <span aria-hidden="true">⌄</span>
    </button>
    <div class="lesson-list">
      {#each lessons as item, index}
        <button class:active={index === selected} onclick={() => choose(index)}>
          <span>Lektion {String(item.number).padStart(2, '0')}</span>
          German A1 노트
        </button>
      {/each}
    </div>
  </div>

  <article class="note-document">
    {#if text}
      <div class="markdown">{@html document}</div>
    {:else}
      <p class="loading">해설서를 불러오는 중…</p>
    {/if}
  </article>
</section>
