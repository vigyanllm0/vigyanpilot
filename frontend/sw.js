const OFFLINE_URL = '/index.html';

const PRECACHE_ASSETS = [
  '/',
  '/index.html',
  '/about.html',
  '/primer.html',
  '/pcr-analysis.html',
  '/demo.html',
  '/404.html',
  '/privacy.html',
  '/terms.html',
  '/refund.html',
  '/security.html',
  '/logo.svg',
  '/manifest.json',
];

const CACHE_VERSION = 21;

self.addEventListener('install', e => {
  self.skipWaiting();
  e.waitUntil(
    caches.keys().then(keys => Promise.all(keys.map(k => caches.delete(k)))).then(() =>
      caches.open('vigyanllm-boot-v' + CACHE_VERSION).then(async cache => {
        for (const url of PRECACHE_ASSETS) {
          try {
            const req = new Request(url, { cache: 'no-store' });
            const res = await fetch(req);
            if (res.ok) {
              await cache.put(req, res);
            }
          } catch (_) {
            // skip failed asset — don't break the install
          }
        }
      })
    )
  );
});

self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys().then(keys => Promise.all(keys.map(k => {
      if (k !== 'vigyanllm-boot-v' + CACHE_VERSION) return caches.delete(k);
    }))).then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', e => {
  if (e.request.method !== 'GET') return;
  const url = new URL(e.request.url);
  if (url.pathname.startsWith('/api/')) return;
  if (url.hostname !== self.location.hostname) return;

  if (e.request.mode === 'navigate') {
    e.respondWith(
      fetch(e.request).catch(() =>
        caches.match(e.request).then(cached => cached || caches.match(OFFLINE_URL))
      )
    );
    return;
  }

  e.respondWith(
    fetch(e.request).catch(() =>
      caches.match(e.request).then(cached => cached || caches.match(OFFLINE_URL))
    )
  );
});
