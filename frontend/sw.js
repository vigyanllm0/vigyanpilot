const CACHE = 'vigyanllm-v3';
const ASSETS = [
  '/',
  '/index.html',
  '/about.html',
  '/primer.html',
  '/demo.html',
  '/sitemap.html',
  '/changelog.html',
  '/404.html',
  '/primer-3-alternative.html',
  '/primer-blast-alternative.html',
  '/validated-primer-design.html',
  '/primer-design-india.html',
  '/biomedical-ai-platform.html',
  '/qpcr-primer-design.html',
  '/primer-design-best-practices.html',
  '/privacy.html',
  '/terms.html',
  '/refund.html',
  '/security.html',
  '/logo.svg',
  '/poster.png',
  '/manifest.json'
];

self.addEventListener('install', e => {
  e.waitUntil(
    caches.open(CACHE).then(c => c.addAll(ASSETS)).then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys().then(keys => Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k))))
  );
});

self.addEventListener('fetch', e => {
  if (e.request.method !== 'GET') return;
  if (e.request.url.startsWith(self.location.origin) && !e.request.url.includes('cdn.') && !e.request.url.includes('googleapis') && !e.request.url.includes('razorpay')) {
    e.respondWith(
      caches.match(e.request).then(cached => cached || fetch(e.request).then(res => {
        const clone = res.clone();
        caches.open(CACHE).then(c => c.put(e.request, clone));
        return res;
      }))
    );
  }
});
