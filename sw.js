// sw.js - Service Worker para PWA + Áudio (VERSÃO VERCEL)
const CACHE_NAME = 'homecare-v2'; // ⚠️ MUDE A VERSÃO A CADA DEPLOY

// Instalação
self.addEventListener('install', (e) => {
    console.log('[SW] Instalando...', CACHE_NAME);
    e.waitUntil(
        caches.open(CACHE_NAME).then((cache) => {
            return cache.addAll([
                '/',
                '/dashboard-cliente',
                '/manifest.json',
                '/icon-192x192.png',
                '/badge-72x72.png'
            ]);
        })
    );
    self.skipWaiting(); // Força ativação imediata
});

// Ativação
self.addEventListener('activate', (e) => {
    console.log('[SW] Ativado!', CACHE_NAME);
    e.waitUntil(
        caches.keys().then((keyList) => {
            return Promise.all(
                keyList.map((key) => {
                    if (key !== CACHE_NAME) {
                        console.log('[SW] Deletando cache antigo:', key);
                        return caches.delete(key);
                    }
                })
            );
        }).then(() => self.clients.claim()) // Assume controle imediato
    );
});

// Interceptação de requisições
self.addEventListener('fetch', (e) => {
    // Cache primeiro, depois rede
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

// 🎵 FUNÇÃO PARA GERAR E TOCAR ÁUDIO (CORRIGIDA PARA VERCEL)
async function gerarETocarAudio(medicationData) {
    try {
        console.log('[SW] Gerando áudio para:', medicationData);
        
        // ✅ USA URL RELATIVA (funciona em localhost E Vercel)
        const baseUrl = self.location.origin;
        
        const response = await fetch(`${baseUrl}/api/generate-audio`, {
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
            // ✅ USA URL COMPLETA COM BASE
            const audioUrl = data.url.startsWith('http') ? data.url : `${baseUrl}${data.url}`;
            const audio = new Audio(audioUrl);
            audio.volume = 1.0;
            await audio.play();
            console.log('[SW] ✅ Áudio tocando!', audioUrl);
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

// Mensagens do frontend
self.addEventListener('message', (e) => {
    if (e.data && e.data.type === 'SKIP_WAITING') {
        self.skipWaiting();
    }
});