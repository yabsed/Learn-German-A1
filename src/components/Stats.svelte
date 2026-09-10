<script lang="ts">
  import { progressSummary } from '../lib/scheduler';
  import type { Progress, Sentence, Word } from '../lib/types';

  interface Props {
    words: Word[];
    sentences: Record<string, Sentence>;
    progress: Progress;
    onReset: () => void;
  }

  let { words, sentences, progress, onReset }: Props = $props();
  let status = $state('');
  let downloading = $state(false);
  let summary = $derived(progressSummary(words, progress));
  let peak = $derived(Math.max(1, ...summary.boxes));
  const boxNames = ['처음', '1일 뒤', '3일 뒤', '1주 뒤', '2주 뒤', '한 달 뒤'];

  async function downloadAll() {
    if (!('caches' in window)) {
      status = '이 브라우저는 오프라인 저장을 지원하지 않습니다.';
      return;
    }
    const urls = words.map((word) => `audio/${word.id}.mp3`)
      .concat(Object.keys(sentences).map((id) => `audio/${id}.mp3`));
    const cache = await caches.open('lgv-audio-v2');
    const queue = [...urls];
    let done = 0;
    let failed = 0;
    downloading = true;

    const worker = async () => {
      for (let url = queue.pop(); url; url = queue.pop()) {
        if (!(await cache.match(url))) {
          try { await cache.add(url); } catch { failed += 1; }
        }
        done += 1;
        if (done % 25 === 0 || done === urls.length) status = `${done} / ${urls.length}개 저장했습니다.`;
      }
    };
    await Promise.all([worker(), worker(), worker(), worker()]);
    downloading = false;
    status = failed
      ? `${urls.length - failed}개를 저장했습니다. ${failed}개는 받지 못했습니다.`
      : `${urls.length}개를 모두 저장했습니다. 이제 인터넷 없이도 됩니다.`;
  }
</script>

<section class="view">
  <div class="tiles">
    <div class="tile"><b>{summary.seen}</b><span>본 단어 / {summary.total}</span></div>
    <div class="tile"><b>{summary.known}</b><span>익힘</span></div>
    <div class="tile"><b>{summary.due}</b><span>오늘 볼 것</span></div>
  </div>
  <h2 class="h2">익힘 단계</h2>
  <div class="bars">
    {#each summary.boxes as count, index}
      <div class="bar"><span>{boxNames[index]}</span><div class="bar-track"><div class="bar-fill" style:width={`${count / peak * 100}%`}></div></div><b>{count}</b></div>
    {/each}
  </div>
  <h2 class="h2">오프라인</h2>
  <p class="hint">A1 오디오 3,264개는 약 26 MB입니다. 한 번 받아 두면 인터넷 없이도 소리가 납니다.</p>
  <button class="btn wide" disabled={downloading} onclick={downloadAll}>오디오 전부 내려받기</button>
  <p class="hint">{status}</p>
  <h2 class="h2">되돌리기</h2>
  <button class="btn wide danger" onclick={onReset}>학습 기록 지우기</button>
</section>
