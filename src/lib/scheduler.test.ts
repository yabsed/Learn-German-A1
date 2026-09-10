import { describe, expect, it } from 'vitest';
import { DAY } from './constants';
import { buildQueue, gradedCard } from './scheduler';
import type { Progress, Word } from './types';

describe('scheduler', () => {
it('puts overdue cards before fresh cards', () => {
  const words = [{ id: 'fresh' }, { id: 'later' }, { id: 'first' }] as Word[];
  const progress: Progress = {
    later: { box: 1, due: 20, seen: 1, ok: 1 },
    first: { box: 1, due: 10, seen: 1, ok: 1 },
  };
  expect(buildQueue(words, progress, 20, 30)).toEqual(['first', 'later', 'fresh']);
});

it('advances correct answers and schedules the next review', () => {
  const next = gradedCard(undefined, true, 1_000);
  expect(next).toMatchObject({ box: 1, seen: 1, ok: 1, due: 1_000 + DAY });
});

it('returns incorrect advanced cards to box one', () => {
  const next = gradedCard({ box: 4, due: 0, seen: 3, ok: 2 }, false, 1_000);
  expect(next).toEqual({ box: 1, due: 1_000, seen: 4, ok: 2 });
});
});
