const CACHE_NAME = 'homecare-v1';
const urlsToCache = [
  '/',
  '/dashboard-cliente',
  '/manifest.json'
];

// Instalação do Service Worker
self.addEventListener('install', event => {
  console.log('[SW] Instalando Service Worker...');
  self.skipWaiting(); // ✅ Força a ativação imediata da nova versão
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => {
        console.log('[SW] Cache aberto');
        return cache.addAll(urlsToCache);
      })
      .catch(err => console.log('[SW] Erro ao cachear:', err))
  );
});

// Ativação do Service Worker
self.addEventListener('activate', event => {
  console.log('[SW] Service Worker ativado');
  event.waitUntil(
    caches.keys().then(cacheNames => {
      return Promise.all(
        cacheNames.map(cacheName => {
          if (cacheName !== CACHE_NAME) {
            return caches.delete(cacheName);
          }
        })
      );
    })
  );
});

// Interceptação de requisições
self.addEventListener('fetch', event => {
  // ✅ CORREÇÃO: Ignora requisições chrome-extension
  if (event.request.url.startsWith('chrome-extension://')) {
    return;
  }
  
  // ✅ CORREÇÃO: Ignora requisições não-http
  if (!event.request.url.startsWith('http')) {
    return;
  }
  
  // ✅ CORREÇÃO: Apenas intercepta/cacheia requisições GET (ignora PUT, POST, DELETE)
  if (event.request.method !== 'GET') {
    return;
  }
  
  // ✅ CORREÇÃO: Não intercepta/cacheia chamadas de API
  if (event.request.url.includes('/api/')) {
    return;
  }
  
  event.respondWith(
    caches.match(event.request)
      .then(response => {
        // Cache hit - retorna do cache
        if (response) {
          return response;
        }
        
        // Clona a requisição
        const fetchRequest = event.request.clone();
        
        return fetch(fetchRequest).then(response => {
          // Verifica se recebemos uma resposta válida
          if (!response || response.status !== 200 || response.type !== 'basic') {
            return response;
          }
          
          // Clona a resposta
          const responseToCache = response.clone();
          
          // Tenta salvar no cache (com try-catch)
          try {
            caches.open(CACHE_NAME)
              .then(cache => {
                cache.put(event.request, responseToCache);
              });
          } catch (err) {
            console.log('[SW] Erro ao salvar no cache:', err);
          }
          
          return response;
        }).catch(err => {
          console.log('[SW] Erro no fetch:', err);
          // Retorna offline page se disponível
          return caches.match('/');
        });
      })
  );
});

// Push notifications
self.addEventListener('push', event => {
  console.log('[SW] Push recebido:', event);
  
  const options = {
    body: event.data ? event.data.text() : 'Você tem um novo lembrete!',
    icon: '/icon-192x192.png',
    badge: '/badge-72x72.png',
    vibrate: [100, 50, 100],
    data: {
      dateOfArrival: Date.now(),
      primaryKey: 1
    },
    actions: [
      {action: 'explore', title: 'Ver Agora'},
      {action: 'close', title: 'Fechar'}
    ]
  };
  
  event.waitUntil(
    self.registration.showNotification('CR$ HOME CARE AI', options)
  );
});

// Notificação click
self.addEventListener('notificationclick', event => {
  console.log('[SW] Notificação clicada:', event);
  
  event.notification.close();
  
  if (event.action === 'explore') {
    event.waitUntil(
      clients.openWindow('/dashboard-cliente')
    );
  }
});

// Mensagens do cliente
self.addEventListener('message', event => {
  console.log('[SW] Mensagem recebida:', event);
  if (event.data && event.data.type === 'SKIP_WAITING') {
    self.skipWaiting();
  }
});

console.log('[SW] Service Worker carregado e pronto!');