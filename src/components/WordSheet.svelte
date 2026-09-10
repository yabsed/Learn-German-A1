<script lang="ts">
  import { tick } from 'svelte';
  import WordDetails from './WordDetails.svelte';
  import type { Sentence, Settings, Word } from '../lib/types';

  interface Props {
    word: Word;
    sentences: Record<string, Sentence>;
    surfaces: Map<string, string>;
    settings: Settings;
    onClose: () => void;
    onPlay: (id: string, button: HTMLButtonElement) => void;
    onWord: (id: string) => void;
  }

  let { word, sentences, surfaces, settings, onClose, onPlay, onWord }: Props = $props();
  $effect(() => {
    word.id;
    tick().then(() => {
      const button = document.querySelector<HTMLButtonElement>('.sheet .play');
      if (button) onPlay(word.id, button);
    });
  });
</script>

<div class="sheet-wrap" role="presentation" onclick={(event) => event.target === event.currentTarget && onClose()}>
  <div class="sheet" role="dialog" aria-modal="true" aria-label="단어 상세">
    <button class="sheet-close" aria-label="닫기" onclick={onClose}>✕</button>
    <div class="lemma sheet-lemma">{word.lemma}</div>
    <div class="sheet-details">
      <WordDetails {word} {sentences} {surfaces} {settings} {onWord} {onPlay} />
    </div>
  </div>
</div>
