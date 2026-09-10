<script lang="ts">
  import WordDetails from './WordDetails.svelte';
  import type { Sentence, Settings, Word } from '../lib/types';

  interface Props {
    word: Word;
    sentences: Record<string, Sentence>;
    surfaces: Map<string, string>;
    wordById: Map<string, Word>;
    settings: Settings;
    playingId?: string;
    onClose: () => void;
    onPlay: (id: string, button: HTMLButtonElement) => void;
    onWord: (id: string) => void;
  }

  let { word, sentences, surfaces, wordById, settings, playingId, onClose, onPlay, onWord }: Props = $props();
</script>

<div class="sheet-wrap" role="presentation" onclick={(event) => event.target === event.currentTarget && onClose()}>
  <div class="sheet" role="dialog" aria-modal="true" aria-label="단어 상세">
    <div class="sheet-nav">
      <button class="sheet-close" aria-label="뒤로 가기" onclick={onClose}>← <span>뒤로</span></button>
    </div>
    <div class="lemma sheet-lemma">{word.lemma}</div>
    <div class="sheet-details">
      <WordDetails {word} {sentences} {surfaces} {wordById} {settings} {playingId} {onWord} {onPlay} />
    </div>
  </div>
</div>
