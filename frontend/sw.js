const CACHE = 'vigyanllm-v7';
const OFFLINE_URL = '/index.html';

const PRECACHE_ASSETS = [
  '/',
  '/index.html',
  '/about.html',
  '/primer.html',
  '/demo.html',
  '/404.html',
  '/privacy.html',
  '/terms.html',
  '/refund.html',
  '/security.html',
  '/logo.svg',
  '/manifest.json',
];

self.addEventListener('install', e => {
  e.waitUntil(
    caches.open(CACHE).then(c => c.addAll(PRECACHE_ASSETS)).then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', e => {
  e.waitUntil(
    Promise.all([
      caches.keys().then(keys =>
        Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k)))
      ),
      self.clients.claim(),
    ])
  );
});

self.addEventListener('fetch', e => {
  if (e.request.method !== 'GET') return;

  const url = new URL(e.request.url);

  // Never intercept API calls
  if (url.pathname.startsWith('/api/')) return;
  // Never cache external CDN resources
  if (url.hostname !== self.location.hostname) return;
  // Always fetch fresh widget JS
  if (url.pathname === '/ai-widget.js') return;

  // Navigation requests: network-first with offline fallback
  if (e.request.mode === 'navigate') {
    e.respondWith(
      fetch(e.request)
        .then(res => {
          const clone = res.clone();
          caches.open(CACHE).then(c => c.put(e.request, clone));
          return res;
        })
        .catch(() => caches.match(e.request).then(cached => cached || caches.match(OFFLINE_URL)))
    );
    return;
  }

  // Static assets: cache-first, network-update
  e.respondWith(
    caches.match(e.request).then(cached => {
      const fetchPromise = fetch(e.request).then(res => {
        const clone = res.clone();
        caches.open(CACHE).then(c => c.put(e.request, clone));
        return res;
      }).catch(() => cached);
      return cached || fetchPromise;
    })
  );
});
