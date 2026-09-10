import { describe, expect, it } from 'vitest';
import { matchesWord } from './search';
import { buildSurfaceIndex, glossParts, sentenceParts } from './words';
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

describe('interlinear glosses', () => {
  const words: Word[] = [
    { id: 'morgen', de: 'morgen', lemma: 'morgen', ko: '내일', ex: [] },
    { id: 'arbeiten', de: 'arbeiten', lemma: 'arbeiten', ko: '일하다', ex: [] },
  ];

  it('reconstructs German groups and keeps punctuation on the preceding group', () => {
    const groups = glossParts(
      'Ab morgen muss ich arbeiten.',
      [[2, '내일부터'], [1, '~해야 한다'], [1, '나는'], [1, '일하다']],
      'arbeiten',
      buildSurfaceIndex(words),
    );
    expect(groups.map(({ de, ko }) => [de, ko])).toEqual([
      ['Ab morgen', '내일부터'], ['muss', '~해야 한다'], ['ich', '나는'], ['arbeiten.', '일하다'],
    ]);
    expect(groups.at(-1)?.parts.find((part) => part.text === 'arbeiten')?.current).toBe(true);
  });

  it('rejects a gloss whose spans do not cover the sentence', () => {
    expect(glossParts('Guten Tag!', [[1, '안녕하세요']], '', new Map())).toEqual([]);
  });

  it('counts a number as a visible gloss token', () => {
    const groups = glossParts('Das kostet 200 Euro.', [[2, '그것은 가격이'], [1, '200'], [1, '유로이다']], '', new Map());
    expect(groups.map((group) => group.de)).toEqual(['Das kostet', '200', 'Euro.']);
  });

  it('keeps workbook alternatives and hyphenated words as single tokens', () => {
    const groups = glossParts(
      'Sonst noch (et)was per E-Mail?',
      [[1, '그 밖에'], [1, '더'], [1, '무엇인가'], [1, '~로'], [1, '이메일']],
      '',
      new Map(),
    );
    expect(groups.map((group) => group.de)).toEqual(['Sonst', 'noch', '(et)was', 'per', 'E-Mail?']);
  });
});

it('includes Korean meanings', () => {
  expect(matchesWord(word, '빵집')).toBe(true);
});
});
