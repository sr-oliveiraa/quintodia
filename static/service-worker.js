const CACHE_NAME = 'my-site-cache-v1';
const urlsToCache = [
    '/',
    '/static/css/styles.css',
    '/static/js/scripts.js',
    '/static/images/logo.png',
    '/static/images/icons/icon-72x72.png',
    '/static/images/icons/icon-96x96.png',
    '/dashboard',
    '/tasks',
    '/login',
    '/register',
    '/expenses',
    '/house_info'

];

self.addEventListener('install', function(event) {
    event.waitUntil(
        caches.open(CACHE_NAME)
            .then(function(cache) {
                console.log('Opened cache');
                return cache.addAll(urlsToCache);
            })
    );
});

self.addEventListener('fetch', function(event) {
    event.respondWith(
        caches.match(event.request)
            .then(function(response) {
                if (response) {
                    return response;
                }
                return fetch(event.request);
            })
    );
});
