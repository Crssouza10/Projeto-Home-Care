// sw.js - Service Worker para PWA + Áudio
const CACHE_NAME = 'homecare-v1';

// Instalação
self.addEventListener('install', (e) => {
    console.log('[SW] Instalando...');
    e.waitUntil(
        caches.open(CACHE_NAME).then((cache) => {
            return cache.addAll([
                '/',
                '/dashboard-cliente',
                '/manifest.json'
            ]);
        })
    );
});

// Ativação
self.addEventListener('activate', (e) => {
    console.log('[SW] Ativado!');
    e.waitUntil(
        caches.keys().then((keyList) => {
            return Promise.all(
                keyList.map((key) => {
                    if (key !== CACHE_NAME) {
                        return caches.delete(key);
                    }
                })
            );
        })
    );
});

// Interceptação de requisições
self.addEventListener('fetch', (e) => {
    e.respondWith(
        caches.match(e.request).then((response) => {
            return response || fetch(e.request);
        })
    );
});

// 🔊 NOTIFICAÇÃO PUSH COM ÁUDIO
self.addEventListener('push', (e) => {
    console.log('[SW] Push recebido!', e);
    
    let data = {};
    try {
        data = e.data.json();
    } catch (err) {
        data = { title: 'Lembrete', body: 'Hora do medicamento!' };
    }
    
    // Toca o áudio antes de mostrar notificação
    const audioPromise = gerarETocarAudio(data.medication);
    
    e.waitUntil(
        audioPromise.then(() => {
            return self.registration.showNotification(data.title || '⏰ Lembrete', {
                body: data.body || 'Hora de tomar seu medicamento!',
                icon: '/icon-192x192.png',
                badge: '/badge-72x72.png',
                vibrate: [200, 100, 200],
                tag: 'medicamento',
                requireInteraction: true,
                data: data
            });
        })
    );
});

// 🎵 FUNÇÃO PARA GERAR E TOCAR ÁUDIO
async function gerarETocarAudio(medicationData) {
    try {
        console.log('[SW] Gerando áudio para:', medicationData);
        
        const response = await fetch('http://localhost:8000/api/generate-audio', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                medication: medicationData.nome || medicationData.medication || 'Medicamento',
                dosage: medicationData.dosagem || medicationData.dosage || '',
                instructions: medicationData.instrucoes || medicationData.instructions || ''
            })
        });
        
        const data = await response.json();
        
        if (data.status === 'success' && data.url) {
            // Toca o áudio
            const audio = new Audio('http://localhost:8000' + data.url);
            audio.volume = 1.0;
            await audio.play();
            console.log('[SW] ✅ Áudio tocando!');
        }
    } catch (error) {
        console.error('[SW] ❌ Erro ao gerar áudio:', error);
    }
}

// Clique na notificação
self.addEventListener('notificationclick', (e) => {
    e.notification.close();
    e.waitUntil(
        clients.openWindow('/dashboard-cliente')
    );
});