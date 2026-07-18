const CACHE_VERSION = 22;

self.addEventListener('install', e => {
  self.skipWaiting();
  e.waitUntil(
    caches.keys().then(keys => Promise.all(keys.map(k => caches.delete(k))))
  );
});

self.addEventListener('activate', e => {
  e.waitUntil(self.clients.claim());
});
