export interface Sentence {
  de: string;
  ko: string;
  en?: string;
}

export interface Word {
  id: string;
  de: string;
  lemma: string;
  article?: string;
  plural?: string;
  ipa?: string;
  ko: string;
  note?: string;
  pos?: string;
  ex: string[];
}

export interface Dataset {
  level: string;
  built: string;
  words: Word[];
  sentences: Record<string, Sentence>;
}

export interface ProgressCard {
  box: number;
  due: number;
  seen: number;
  ok: number;
}

export type Progress = Record<string, ProgressCard>;

export interface Settings {
  autoplay: boolean;
  english: boolean;
  hideKorean: boolean;
  session: number;
}

export type View = 'practice' | 'browse' | 'stats';
export type WordFilter = 'all' | 'new' | 'learning' | 'known';
