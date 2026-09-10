import type { Progress, Word, WordFilter } from './types';

export function fold(text: string, spellUmlauts = false): string {
  const map = spellUmlauts
    ? { ä: 'ae', ö: 'oe', ü: 'ue' }
    : { ä: 'a', ö: 'o', ü: 'u' };
  return String(text).toLowerCase()
    .replace(/[äöü]/g, (letter) => map[letter as keyof typeof map])
    .replace(/ß/g, 'ss')
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '');
}

export function wordHaystack(word: Word): string {
  const raw = [word.de, word.lemma, word.ko, word.note || ''].join(' ');
  const bare = fold(raw);
  const spelled = fold(raw, true);
  return bare + (spelled === bare ? '' : ` ${spelled}`);
}

export function matchesWord(word: Word, query: string): boolean {
  return !query || wordHaystack(word).includes(fold(query.trim()));
}

export function passesFilter(word: Word, filter: WordFilter, progress: Progress, topBox: number): boolean {
  const card = progress[word.id];
  if (filter === 'new') return !card;
  if (filter === 'learning') return Boolean(card) && card.box < topBox;
  if (filter === 'known') return Boolean(card) && card.box >= topBox;
  return true;
}
