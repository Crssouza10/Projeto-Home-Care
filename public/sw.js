// public/sw.js
self.addEventListener('push', event => {
    const data = event.data.json();
    
    self.registration.showNotification(data.title, {
        body: data.body,
        icon: '/icon-192x192.png',
        badge: '/badge-72x72.png',
        vibrate: [200, 100, 200],
        data: data.data,
        actions: [
            { action: 'taken', title: '✅ Tomei' },
            { action: 'later', title: '⏰ Reagendar' }
        ]
    });
});

self.addEventListener('notificationclick', event => {
    event.notification.close();
    
    if (event.action === 'taken') {
        // Marcar como tomado
        fetch(`/api/medications/${event.notification.data.medication_id}/take`, {
            method: 'POST'
        });
    } else if (event.action === 'later') {
        // Abrir app para reagendar
        event.waitUntil(clients.openWindow('/dashboard-cliente'));
    }
});