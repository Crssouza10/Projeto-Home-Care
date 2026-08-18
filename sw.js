// Service Worker para Cuidadoso v1.6
// Suporta PWA básica e Notificações Push em background (segundo plano)

self.addEventListener('install', event => {
    self.skipWaiting();
});

self.addEventListener('activate', event => {
    event.waitUntil(clients.claim());
});

self.addEventListener('fetch', event => {
    // Deixa requisições externas/terceiros (como analytics, Mercado Pago) passarem direto sem interceptação do SW
    if (!event.request.url.startsWith(self.location.origin)) {
        return;
    }
    
    // Pass-through com fallback de erro suave para nossa própria origem
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

    const medId = event.notification.data?.medication_id;

    // Botão "Tomei" → registra a tomada em background (sem abrir o app)
    if (event.action === 'taken') {
        if (medId) {
            event.waitUntil(
                fetch(`/api/medications/${medId}/take`, { method: 'POST' })
                    .then(() => console.log('[SW] Medicamento marcado como tomado (background)'))
                    .catch(err => console.error('[SW] Erro ao marcar como tomado:', err))
            );
        }
        return;
    }

    // Botão "Reagendar" (CTG-107) → adia a dose de hoje em +15 minutos via API.
    // Se a API recusar (conflito de horário, etc.), abre o app para reagendamento manual.
    if (event.action === 'later') {
        if (medId) {
            event.waitUntil(
                (async () => {
                    try {
                        const now = new Date();
                        now.setMinutes(now.getMinutes() + 15);
                        const hh = String(now.getHours()).padStart(2, '0');
                        const mm = String(now.getMinutes()).padStart(2, '0');
                        const res = await fetch(
                            `/api/medications/${medId}/reschedule?new_time=${hh}:${mm}`,
                            { method: 'PUT' }
                        );
                        if (!res.ok) {
                            console.warn('[SW] Reagendamento automático recusado, abrindo app:', res.status);
                            return clients.openWindow('/dashboard-cliente');
                        }
                        console.log('[SW] Dose reagendada para +15min:', `${hh}:${mm}`);
                    } catch (err) {
                        console.error('[SW] Erro ao reagendar:', err);
                        return clients.openWindow('/dashboard-cliente');
                    }
                })()
            );
            return;
        }
    }

    // Clique no corpo da notificação → abre (ou foca) o dashboard
    event.waitUntil(
        clients.matchAll({ type: 'window' }).then(windowClients => {
            for (let i = 0; i < windowClients.length; i++) {
                const client = windowClients[i];
                if (client.url.includes('/dashboard-cliente') && 'focus' in client) {
                    return client.focus();
                }
            }
            if (clients.openWindow) {
                return clients.openWindow('/dashboard-cliente');
            }
        })
    );
});
