const CACHE_NAME = 'homecare-v1.2';
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
  
  let title = '💊 CR$ HOME CARE AI';
  let body = 'Você tem um novo lembrete!';
  let icon = '/static/icons/icon-192x192.png';
  let badge = '/static/icons/icon-72x72.png';
  let notificationData = { url: '/dashboard-cliente' };
  let actions = [
    {action: 'explore', title: '🔍 Abrir Painel'},
    {action: 'close', title: 'Fechar'}
  ];
  
  if (event.data) {
    try {
      const payload = event.data.json();
      title = payload.title || title;
      body = payload.body || body;
      icon = payload.icon || icon;
      badge = payload.badge || badge;
      if (payload.data) {
        notificationData = { ...notificationData, ...payload.data };
      }
      
      // Se houver ID do medicamento, adiciona ação direta de confirmação no push
      if (payload.data && payload.data.medication_id) {
        actions = [
          {action: 'take', title: '✅ Tomei o Remédio'},
          {action: 'explore', title: '🔍 Abrir'}
        ];
      }
    } catch (e) {
      console.warn('[SW] Payload não é JSON válido, tratando como texto:', e);
      body = event.data.text();
    }
  }
  
  const options = {
    body: body,
    icon: icon,
    badge: badge,
    vibrate: [200, 100, 200, 100, 200],
    data: notificationData,
    actions: actions,
    tag: notificationData.medication_id || 'med-alert',
    requireInteraction: true // Notificação fica fixa até o usuário interagir
  };
  
  event.waitUntil(
    self.registration.showNotification(title, options)
  );
});

// Notificação click
self.addEventListener('notificationclick', event => {
  console.log('[SW] Notificação clicada:', event);
  
  event.notification.close();
  
  const targetUrl = event.notification.data && event.notification.data.url 
    ? event.notification.data.url 
    : '/dashboard-cliente';
  
  if (event.action === 'take') {
    const medId = event.notification.data.medication_id;
    if (medId) {
      event.waitUntil(
        fetch(`/api/medications/${medId}/take`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' }
        })
        .then(response => {
          if (response.ok) {
            console.log('[SW] Confirmado como tomado com sucesso!');
            // Envia mensagem para abas abertas recarregarem os dados
            return self.clients.matchAll({ type: 'window', includeUncontrolled: true }).then(clientList => {
              clientList.forEach(client => {
                client.postMessage({
                  type: 'MEDICAMENTO_TOMADO_BACKGROUND',
                  medicationId: medId
                });
              });
            });
          }
        })
        .catch(err => {
          console.error('[SW] Erro ao registrar tomada do remédio:', err);
        })
      );
    }
  } else {
    // Ação padrão (clicou no card ou no botão explorar)
    event.waitUntil(
      self.clients.matchAll({ type: 'window', includeUncontrolled: true }).then(clientList => {
        // Tenta focar em uma aba que já esteja aberta no dashboard
        for (const client of clientList) {
          if (client.url.includes(targetUrl) && 'focus' in client) {
            return client.focus();
          }
        }
        // Se não tiver aba aberta, abre uma nova
        if (self.clients.openWindow) {
          return self.clients.openWindow(targetUrl);
        }
      })
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