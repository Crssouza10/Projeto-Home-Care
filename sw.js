// Service Worker para Cuidadoso v1.6
// Suporta PWA básica e Notificações Push em background (segundo plano)

self.addEventListener('install', event => {
    self.skipWaiting();
});

self.addEventListener('activate', event => {
    event.waitUntil(clients.claim());
});

self.addEventListener('fetch', event => {
    // Pass-through com fallback de erro suave
    event.respondWith(
        fetch(event.request).catch(error => {
            console.warn('[SW] Falha na rede para:', event.request.url);
            return new Response('Erro de Conexão ou Servidor Indisponível (503)', {
                status: 503,
                statusText: 'Service Unavailable',
                headers: { 'Content-Type': 'text/plain; charset=utf-8' }
            });
        })
    );
});

// Listener para receber notificações Push mesmo com a aplicação fechada
self.addEventListener('push', event => {
    try {
        const data = event.data.json();
        
        const options = {
            body: data.body,
            icon: data.icon || '/icon-192x192.png',
            badge: data.badge || '/badge-72x72.png',
            vibrate: [300, 100, 300, 100, 300], // vibração mais intensa
            data: data.data || {},
            actions: [
                { action: 'taken', title: '✅ Tomei' },
                { action: 'later', title: '⏰ Reagendar' }
            ],
            requireInteraction: true // A notificação fica ativa na tela até que o usuário interaja
        };
        
        event.waitUntil(
            self.registration.showNotification(data.title || '💊 Hora do Medicamento!', options)
        );
    } catch (err) {
        console.error('Erro ao processar push event:', err);
    }
});

// Listener para quando o usuário clica na notificação ou nas ações dela
self.addEventListener('notificationclick', event => {
    event.notification.close();
    
    // Se o usuário clicou no botão "Tomei"
    if (event.action === 'taken') {
        const medId = event.notification.data?.medication_id;
        if (medId) {
            event.waitUntil(
                fetch(`/api/medications/${medId}/take`, {
                    method: 'POST'
                }).then(response => {
                    console.log('Medicamento marcado como tomado via background');
                }).catch(err => {
                    console.error('Erro ao marcar como tomado via background:', err);
                })
            );
        }
    } else {
        // Se clicou na própria notificação ou em "Reagendar", abre o app
        event.waitUntil(
            clients.matchAll({ type: 'window' }).then(windowClients => {
                // Se já tiver uma aba aberta, foca nela
                for (let i = 0; i < windowClients.length; i++) {
                    const client = windowClients[i];
                    if (client.url.includes('/dashboard-cliente') && 'focus' in client) {
                        return client.focus();
                    }
                }
                // Senão, abre uma nova aba
                if (clients.openWindow) {
                    return clients.openWindow('/dashboard-cliente');
                }
            })
        );
    }
});
