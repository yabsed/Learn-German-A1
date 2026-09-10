import { DAY, INTERVALS, TOP_BOX } from './constants';
import type { Progress, ProgressCard, Word } from './types';

export const emptyCard = (): ProgressCard => ({ box: 0, due: 0, seen: 0, ok: 0 });

export function buildQueue(words: Word[], progress: Progress, size: number, now = Date.now()): string[] {
  const due: string[] = [];
  const fresh: string[] = [];
  for (const word of words) {
    const card = progress[word.id];
    if (!card) fresh.push(word.id);
    else if (card.due <= now) due.push(word.id);
  }
  due.sort((a, b) => progress[a].due - progress[b].due);
  const all = due.concat(fresh);
  return size > 0 ? all.slice(0, size) : all;
}

export function gradedCard(previous: ProgressCard | undefined, ok: boolean, now = Date.now()): ProgressCard {
  const next = { ...emptyCard(), ...previous };
  next.seen += 1;
  if (ok) {
    next.ok += 1;
    next.box = Math.min(next.box + 1, TOP_BOX);
  } else {
    next.box = next.box > 1 ? 1 : 0;
  }
  next.due = ok ? now + INTERVALS[next.box] * DAY : now;
  return next;
}

export function progressSummary(words: Word[], progress: Progress, now = Date.now()) {
  const boxes = new Array(INTERVALS.length).fill(0);
  let seen = 0;
  let known = 0;
  let due = 0;
  for (const word of words) {
    const card = progress[word.id];
    if (!card) continue;
    seen += 1;
    boxes[card.box] += 1;
    if (card.box >= TOP_BOX) known += 1;
    if (card.due <= now) due += 1;
  }
  return { total: words.length, seen, known, due: due + words.length - seen, boxes };
}
