const CACHE_NAME = 'gerenciamento-domestico-cache-v1';
const urlsToCache = [
  '/',
  '/static/css/styles.css',
  '/static/js/scripts.js',
  '/static/img/icon-192x192.png',
  '/static/img/icon-512x512.png',
  // Adicione outras URLs que você deseja armazenar em cache
];

self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => {
        return cache.addAll(urlsToCache);
      })
  );
});

self.addEventListener('fetch', event => {
  event.respondWith(
    caches.match(event.request)
      .then(response => {
        if (response) {
          return response;
        }
        return fetch(event.request);
      })
  );
});
