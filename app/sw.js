/* 서비스 워커. 두 캐시를 나눠 쓴다.
 *
 *   lgv-shell-v1  HTML·CSS·JS·단어 파일. 설치할 때 통째로 받는다. 작다.
 *   lgv-audio-v1  mp3. 재생한 것만 남기거나, 진도 화면에서 한 번에 받는다.
 *
 * 오디오를 셸에 섞지 않는 이유는 24 MB 를 첫 방문에 받게 하지 않기 위해서다. */

const SHELL = 'lgv-shell-v1';
const AUDIO = 'lgv-audio-v1';

const SHELL_FILES = [
  '.', 'index.html', 'style.css', 'app.js',
  'manifest.webmanifest', 'icon.svg', 'icon-192.png', 'icon-512.png',
  'data/a1.json',
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(SHELL).then((cache) => cache.addAll(SHELL_FILES)).then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys()
      .then((names) => Promise.all(
        names.filter((n) => n !== SHELL && n !== AUDIO).map((n) => caches.delete(n))
      ))
      .then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (event) => {
  const request = event.request;
  if (request.method !== 'GET') return;

  const url = new URL(request.url);
  if (url.origin !== self.location.origin) return;

  // mp3 는 한 번 받으면 바뀌지 않는다. 있으면 그것을 주고, 없으면 받아서 남긴다.
  if (url.pathname.endsWith('.mp3')) {
    event.respondWith(
      caches.open(AUDIO).then(async (cache) => {
        const hit = await cache.match(request);
        if (hit) return hit;
        const response = await fetch(request);
        if (response.ok) cache.put(request, response.clone());
        return response;
      }).catch(() => new Response('', { status: 504 }))
    );
    return;
  }

  // 나머지는 새것을 먼저 시도하고, 안 되면 캐시로 버틴다.
  event.respondWith(
    fetch(request)
      .then((response) => {
        if (response.ok) {
          const copy = response.clone();
          caches.open(SHELL).then((cache) => cache.put(request, copy));
        }
        return response;
      })
      .catch(async () => (await caches.match(request)) || caches.match('index.html'))
  );
});
