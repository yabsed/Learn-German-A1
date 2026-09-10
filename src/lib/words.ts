import type { Word } from './types';

const WORD_RE = /[A-Za-zÄÖÜäöüß]+/g;

export interface SentencePart {
  text: string;
  wordId?: string;
  current?: boolean;
}

export function buildSurfaceIndex(words: Word[]): Map<string, string> {
  const index = new Map<string, string>();
  const put = (text: string | undefined, id: string) => {
    const key = (text || '').toLowerCase();
    if (key && !index.has(key)) index.set(key, id);
  };
  for (const word of words) put(word.lemma, word.id);
  for (const word of words) put(word.plural?.split(/\s+/).at(-1), word.id);
  return index;
}

export function sentenceParts(text: string, currentId: string, surfaces: Map<string, string>): SentencePart[] {
  const parts: SentencePart[] = [];
  let at = 0;
  for (const match of text.matchAll(WORD_RE)) {
    const index = match.index ?? 0;
    if (index > at) parts.push({ text: text.slice(at, index) });
    const wordId = surfaces.get(match[0].toLowerCase());
    parts.push({ text: match[0], wordId, current: wordId === currentId });
    at = index + match[0].length;
  }
  if (at < text.length) parts.push({ text: text.slice(at) });
  return parts;
}
