<script lang="ts">
  import type { Settings, View } from '../lib/types';

  interface Props {
    view: View;
    settings: Settings;
    progressPercent: number;
    practiceFinished: boolean;
    onNavigate: (view: View) => void;
    onSettingsChange: (settings: Settings) => void;
  }

  let { view, settings, progressPercent, practiceFinished, onNavigate, onSettingsChange }: Props = $props();
  let settingsOpen = $state(false);

  function update<K extends keyof Settings>(key: K, value: Settings[K]) {
    onSettingsChange({ ...settings, [key]: value });
  }
</script>

<header class="top">
  <div class="top-row">
    <h1><span class="badge">A1</span> 발음 연습</h1>
    <button class="icon-btn" aria-label="설정" aria-expanded={settingsOpen} onclick={() => settingsOpen = !settingsOpen}>⚙</button>
  </div>
  <nav class="tabs" aria-label="주요 화면">
    {#each [['practice', '연습'], ['browse', '단어장'], ['stats', '진도']] as tab}
      <button
        class="tab"
        aria-current={view === tab[0] ? 'page' : undefined}
        onclick={() => onNavigate(tab[0] as View)}
      >{tab[1]}</button>
    {/each}
  </nav>
  {#if view === 'practice' && !practiceFinished}
    <div class="daybar"><div class="daybar-fill" style:width={`${progressPercent}%`}></div></div>
  {/if}
</header>

{#if settingsOpen}
  <div class="panel">
    <label class="opt"><input type="checkbox" checked={settings.autoplay} onchange={(e) => update('autoplay', e.currentTarget.checked)}> 뜻을 열면 소리를 자동으로 낸다</label>
    <label class="opt"><input type="checkbox" checked={settings.english} onchange={(e) => update('english', e.currentTarget.checked)}> 예문에 영어도 보여 준다</label>
    <label class="opt"><input type="checkbox" checked={settings.hideKorean} onchange={(e) => update('hideKorean', e.currentTarget.checked)}> 예문 뜻은 눌러야 보인다</label>
    <label class="opt">한 세션 분량
      <select value={settings.session} onchange={(e) => update('session', Number(e.currentTarget.value))}>
        <option value="10">10개</option>
        <option value="20">20개</option>
        <option value="40">40개</option>
        <option value="0">끝까지</option>
      </select>
    </label>
  </div>
{/if}
