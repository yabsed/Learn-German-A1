export interface Sentence {
  de: string;
  ko: string;
  en?: string;
  /** [독일어 낱말 수, 문맥상 한국어 뜻, 해당 독일어 표현의 오디오 id]. */
  g?: Array<[number, string, string]>;
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
  /** 표제어 외에 이 단어 상세로 연결할 수 있는 활용·복수형. */
  variants?: string[];
  ex: string[];
}

export interface Dataset {
  level: string;
  built: string;
  words: Word[];
  sentences: Record<string, Sentence>;
  audio?: { files: number; bytes: number };
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
