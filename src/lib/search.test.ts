import { describe, expect, it } from 'vitest';
import { matchesWord } from './search';
import { buildSurfaceIndex, sentenceParts } from './words';
import type { Word } from './types';

const word: Word = { id: 'baeckerei', de: 'die Bäckerei', lemma: 'Bäckerei', ko: '빵집', note: '', ex: [] };

describe('word search', () => {
it('accepts plain and spelled umlauts', () => {
  expect(matchesWord(word, 'backerei')).toBe(true);
  expect(matchesWord(word, 'baeckerei')).toBe(true);
  expect(matchesWord(word, 'Bäckerei')).toBe(true);
});

describe('word variants', () => {
  const verb: Word = { id: 'anrufen', de: 'anrufen', lemma: 'anrufen', ko: '전화하다', variants: ['ruft', 'angerufen'], ex: [] };

  it('links a declared inflected form to its lemma card', () => {
    const parts = sentenceParts('Peter ruft an.', 'other', buildSurfaceIndex([verb]));
    expect(parts.find((part) => part.text === 'ruft')?.wordId).toBe('anrufen');
  });

  it('does not overwrite a direct lemma with an ambiguous variant', () => {
    const particle: Word = { id: 'an', de: 'an', lemma: 'an', ko: '~에', ex: [] };
    expect(buildSurfaceIndex([particle, verb]).get('an')).toBe('an');
  });
});

it('includes Korean meanings', () => {
  expect(matchesWord(word, '빵집')).toBe(true);
});
});
