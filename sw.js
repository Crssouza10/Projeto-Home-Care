// Service Worker para CR$ Home Care AI - Versão Corrigida
const CACHE_NAME = 'homecare-v1';
const ASSETS_TO_CACHE = [
  '/',
  '/dashboard-cliente',
  'https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap'
];

// Instalação: Cache apenas de assets estáticos
self.addEventListener('install', (event) => {
  console.log('[SW] Instalando...');
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      console.log('[SW] Cache aberto:', CACHE_NAME);
      return cache.addAll(ASSETS_TO_CACHE).catch(err => {
        console.log('[SW] Alguns assets não foram cacheados:', err);
      });
    })
  );
  self.skipWaiting();
});

// Ativação: Limpar caches antigos
self.addEventListener('activate', (event) => {
  console.log('[SW] Ativando...');
  event.waitUntil(
    caches.keys().then((keys) => {
      return Promise.all(
        keys.filter((key) => key !== CACHE_NAME).map((key) => {
          console.log('[SW] Removendo cache antigo:', key);
          return caches.delete(key);
        })
      );
    })
  );
  self.clients.claim();
});

// Fetch: Estratégia inteligente
self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // ✅ IMPORTANTE: Requisições API SEMPRE vão para a rede (nunca cache)
  if (url.pathname.startsWith('/api/')) {
    // Ignora requisições POST (login, criar, atualizar)
    if (request.method === 'POST' || request.method === 'PUT' || request.method === 'DELETE') {
      return; // Deixa passar direto para o servidor
    }
    
    // GET em API: Rede primeiro, sem cache
    event.respondWith(
      fetch(request).catch(() => {
        console.log('[SW] API offline:', request.url);
        return new Response(JSON.stringify({ error: 'Offline' }), {
          status: 503,
          headers: { 'Content-Type': 'application/json' }
        });
      })
    );
    return;
  }

  // Assets estáticos: Cache primeiro
  event.respondWith(
    caches.match(request).then((cached) => {
      const fetchPromise = fetch(request).then((networkResp) => {
        if (networkResp && networkResp.ok) {
          const respClone = networkResp.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(request, respClone));
        }
        return networkResp;
      }).catch(() => {
        console.log('[SW] Asset offline:', request.url);
        return cached;
      });
      
      return cached || fetchPromise;
    })
  );
});

// Push Notifications (preparação para futuro)
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