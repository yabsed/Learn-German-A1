import type { Word } from './types';

const WORD_RE = /[A-Za-zÄÖÜäöüß]+/g;
const GLOSS_TOKEN_RE = /(?:\([A-Za-zÄÖÜäöüß]+\))?[A-Za-zÄÖÜäöüß]+(?:[-/][A-Za-zÄÖÜäöüß]+)*|\d+(?:[.,:]\d+)*/g;

export interface SentencePart {
  text: string;
  wordId?: string;
  current?: boolean;
}

export interface GlossPart {
  de: string;
  ko: string;
  audioId: string;
  parts: SentencePart[];
}

export function buildSurfaceIndex(words: Word[]): Map<string, string> {
  const index = new Map<string, string>();
  const put = (text: string | undefined, id: string) => {
    const key = (text || '').toLowerCase();
    if (key && !index.has(key)) index.set(key, id);
  };
  for (const word of words) put(word.lemma, word.id);
  for (const word of words) put(word.plural?.split(/\s+/).at(-1), word.id);
  // `variants` is generated from the source word list's explicitly supplied
  // forms.  It deliberately wins neither over a lemma nor over a plural: an
  // ambiguous surface should keep its more specific dictionary entry.
  for (const word of words) {
    for (const form of word.variants || []) put(form, word.id);
  }
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

export function glossParts(
  text: string,
  gloss: Array<[number, string, string]> | undefined,
  currentId: string,
  surfaces: Map<string, string>,
): GlossPart[] {
  if (!gloss?.length) return [];
  const words = [...text.matchAll(GLOSS_TOKEN_RE)];
  if (
    gloss.some(([span, meaning, audioId]) => !Number.isInteger(span) || span < 1 || !meaning.trim() || !audioId)
    || gloss.reduce((total, [span]) => total + span, 0) !== words.length
  ) return [];

  const groups: GlossPart[] = [];
  let wordAt = 0;
  for (const [span, meaning, audioId] of gloss) {
    const first = words[wordAt];
    const next = words[wordAt + span];
    const start = wordAt === 0 ? 0 : (first.index ?? 0);
    const end = next ? (next.index ?? text.length) : text.length;
    const de = text.slice(start, end).trim();
    groups.push({ de, ko: meaning.trim(), audioId, parts: sentenceParts(de, currentId, surfaces) });
    wordAt += span;
  }
  return groups;
}
