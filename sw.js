// Service Worker para CR$ Home Care AI - Cache Offline Básico
const CACHE_NAME = 'homecare-v1';
const ASSETS_TO_CACHE = [
  '/',
  '/dashboard-cliente',
  '/api/cliente/login',
  'https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap'
];

// Instalação: Cache dos assets críticos
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      console.log('[SW] Cache aberto:', CACHE_NAME);
      return cache.addAll(ASSETS_TO_CACHE).catch(err => {
        console.log('[SW] Erro ao cachear assets:', err);
      });
    })
  );
  self.skipWaiting();
});

// Ativação: Limpar caches antigos
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) => {
      return Promise.all(
        keys.filter((key) => key !== CACHE_NAME).map((key) => caches.delete(key))
      );
    })
  );
  self.clients.claim();
});

// Fetch: Estratégia Cache-First para assets, Network-First para API
self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // API: Tenta rede primeiro, fallback para cache se offline
  if (url.pathname.startsWith('/api/')) {
    event.respondWith(
      fetch(request)
        .catch(() => caches.match(request))
    );
    return;
  }

  // Assets estáticos: Cache primeiro, atualiza em background
  event.respondWith(
    caches.match(request).then((cached) => {
      const fetchPromise = fetch(request).then((networkResp) => {
        if (networkResp && networkResp.ok) {
          const respClone = networkResp.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(request, respClone));
        }
        return networkResp;
      }).catch(() => cached);
      
      return cached || fetchPromise;
    })
  );
});

// Push Notifications (preparação para Fase 1 - Etapa 3)
self.addEventListener('push', (event) => {
  const data = event.data?.json() || {};
  const options = {
    body: data.body || 'Você tem um novo lembrete!',
    icon: 'https://cdn-icons-png.flaticon.com/512/3135/3135715.png',
    badge: 'https://cdn-icons-png.flaticon.com/512/3135/3135715.png',
    vibrate: [100, 50, 100],
    data: { url: data.url || '/dashboard-cliente' },
    actions: [
      { action: 'open', title: 'Abrir App' },
      { action: 'dismiss', title: 'Dispensar' }
    ]
  };

  event.waitUntil(
    self.registration.showNotification(data.title || 'CR$ Home Care AI', options)
  );
});

// Clique na notificação
self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  if (event.action === 'open' || !event.action) {
    event.waitUntil(
      clients.openWindow(event.notification.data.url)
    );
  }
});