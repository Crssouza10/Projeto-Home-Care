// Service Worker mínimo para Cuidadoso v1.5
// Evita erro 404 e habilita PWA básica

self.addEventListener('install', event => {
    self.skipWaiting();
});

self.addEventListener('activate', event => {
    event.waitUntil(clients.claim());
});

self.addEventListener('fetch', event => {
    // Pass-through: não intercepta requisições
    event.respondWith(fetch(event.request));
});
