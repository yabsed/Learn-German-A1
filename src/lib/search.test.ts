import { describe, expect, it } from 'vitest';
import { matchesWord } from './search';
import type { Word } from './types';

const word: Word = { id: 'baeckerei', de: 'die Bäckerei', lemma: 'Bäckerei', ko: '빵집', note: '', ex: [] };

describe('word search', () => {
it('accepts plain and spelled umlauts', () => {
  expect(matchesWord(word, 'backerei')).toBe(true);
  expect(matchesWord(word, 'baeckerei')).toBe(true);
  expect(matchesWord(word, 'Bäckerei')).toBe(true);
});

it('includes Korean meanings', () => {
  expect(matchesWord(word, '빵집')).toBe(true);
});
});
