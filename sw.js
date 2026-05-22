// ============================================================
//  SERVICE WORKER - CR$ HOME CARE AI
//  Funções: Cache Offline + Notificações Push + Fetch Strategy
// ============================================================

const CACHE_NAME = 'homecare-v2'; // Versão atualizada

// Assets críticos para cache offline
const ASSETS_TO_CACHE = [
  '/',
  '/dashboard-cliente',
  '/manifest.json',
  'https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap'
];

// ============================================================
//  INSTALAÇÃO: Cache dos assets estáticos
// ============================================================
self.addEventListener('install', (event) => {
  console.log('[SW] 🔄 Instalando Service Worker...');
  
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then((cache) => {
        console.log('[SW] 📦 Cache aberto:', CACHE_NAME);
        return cache.addAll(ASSETS_TO_CACHE).catch(err => {
          console.log('[SW] ⚠️ Alguns assets não foram cacheados:', err);
        });
      })
      .then(() => self.skipWaiting())
  );
});

// ============================================================
//  ATIVAÇÃO: Limpar caches antigos e assumir controle
// ============================================================
self.addEventListener('activate', (event) => {
  console.log('[SW] ✅ Service Worker ativado');
  
  event.waitUntil(
    caches.keys().then((keys) => {
      return Promise.all(
        keys
          .filter((key) => key !== CACHE_NAME)
          .map((key) => {
            console.log('[SW] 🗑️ Removendo cache antigo:', key);
            return caches.delete(key);
          })
      );
    })
    .then(() => self.clients.claim())
  );
});

// ============================================================
//  FETCH: Estratégia inteligente de rede/cache
// ============================================================
self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // 🚫 API: Sempre vai para a rede (nunca cache)
  if (url.pathname.startsWith('/api/')) {
    // Requisições de escrita (POST/PUT/DELETE) passam direto
    if (['POST', 'PUT', 'DELETE', 'PATCH'].includes(request.method)) {
      return; 
    }
    
    // GET em API: Rede primeiro, fallback offline amigável
    event.respondWith(
      fetch(request)
        .catch(() => {
          console.log('[SW] 📡 API offline:', request.url);
          return new Response(
            JSON.stringify({ error: 'Você está offline. Conecte-se para sincronizar.' }), 
            {
              status: 503,
              headers: { 'Content-Type': 'application/json' }
            }
          );
        })
    );
    return;
  }

  // 📦 Assets estáticos: Cache-first com atualização em background
  event.respondWith(
    caches.match(request).then((cached) => {
      const fetchPromise = fetch(request)
        .then((networkResp) => {
          // Atualiza o cache se a resposta for válida
          if (networkResp && networkResp.ok) {
            const respClone = networkResp.clone();
            caches.open(CACHE_NAME).then((cache) => cache.put(request, respClone));
          }
          return networkResp;
        })
        .catch(() => {
          console.log('[SW] 📦 Asset offline, servindo do cache:', request.url);
          return cached;
        });
      
      return cached || fetchPromise;
    })
  );
});

// ============================================================
//  PUSH NOTIFICATIONS: Receber e exibir notificações
// ============================================================
self.addEventListener('push', (event) => {
  console.log('[SW] 🔔 Push recebido');
  
  if (!event.data) return;
  
  try {
    const data = event.data.json();
    
    const options = {
      body: data.body || 'Você tem um novo lembrete de saúde!',
      icon: data.icon || 'https://cdn-icons-png.flaticon.com/512/3135/3135715.png',
      badge: data.badge || 'https://cdn-icons-png.flaticon.com/512/3135/3135715.png',
      vibrate: [100, 50, 100, 50, 100],
      tag: data.tag || 'homecare-notification',
      renotify: true,
      requireInteraction: true,
      data: { 
        url: data.url || '/dashboard-cliente',
        med_id: data.med_id || null,
        timestamp: Date.now()
      },
      actions: [
        { 
          action: 'open', 
          title: '👉 Abrir App',
          icon: 'https://cdn-icons-png.flaticon.com/512/3135/3135715.png'
        },
        { 
          action: 'snooze', 
          title: '⏰ Lembre em 10min'
        },
        { 
          action: 'dismiss', 
          title: '❌ Dispensar'
        }
      ]
    };

    event.waitUntil(
      self.registration.showNotification(data.title || '💊 CR$ Home Care AI', options)
    );
    
  } catch (err) {
    console.error('[SW] ❌ Erro ao processar push:', err);
  }
});

// ============================================================
//  NOTIFICATION CLICK: Ações ao clicar na notificação
// ============================================================
self.addEventListener('notificationclick', (event) => {
  console.log('[SW] 🖱️ Notificação clicada:', event.action);
  
  event.notification.close();
  
  const urlToOpen = event.notification.data?.url || '/dashboard-cliente';
  
  // Ação: Abrir App
  if (event.action === 'open' || !event.action) {
    event.waitUntil(
      clients.matchAll({ type: 'window', includeUncontrolled: true })
        .then((clientList) => {
          // Se já existe uma aba do app, foca nela
          for (const client of clientList) {
            if (client.url.includes('dashboard-cliente') && 'focus' in client) {
              return client.focus();
            }
          }
          // Senão, abre uma nova
          if (clients.openWindow) {
            return clients.openWindow(urlToOpen);
          }
        })
    );
  }
  
  // Ação: Adiar (Snooze) - pode ser expandido no futuro
  else if (event.action === 'snooze') {
    console.log('[SW] ⏰ Usuário pediu para adiar lembrete');
    // Aqui você poderia enviar um fetch para o backend registrar o snooze
    event.waitUntil(
      self.registration.showNotification('⏰ Lembrete adiado', {
        body: 'Vamos te lembrar novamente em 10 minutos.',
        icon: 'https://cdn-icons-png.flaticon.com/512/3135/3135715.png'
      })
    );
  }
  
  // Ação: Dispensar
  else if (event.action === 'dismiss') {
    console.log('[SW] ❌ Usuário dispensou o lembrete');
  }
});

// ============================================================
//  MENSAGENS DO CLIENTE (comunicação frontend ↔ SW)
// ============================================================
self.addEventListener('message', (event) => {
  if (event.data && event.data.type === 'SKIP_WAITING') {
    self.skipWaiting();
  }
  
  if (event.data && event.data.type === 'GET_CACHE_STATUS') {
    caches.keys().then((keys) => {
      event.ports[0].postMessage({ caches: keys, active: CACHE_NAME });
    });
  }
});

// ============================================================
//  LOGS DE DIAGNÓSTICO (opcional, remova em produção)
// ============================================================
self.addEventListener('error', (event) => {
  console.error('[SW] 💥 Erro global no Service Worker:', event.message);
});

console.log('[SW] 🚀 Service Worker carregado e pronto!');