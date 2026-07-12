/**
 * Service Worker - AI Exam Checker PWA
 * Caches static assets for offline use
 */
const CACHE_NAME = 'ai-exam-checker-v1';
const STATIC_ASSETS = [
  '/pages/login.html',
  '/pages/dashboard.html',
  '/pages/scanner.html',
  '/assets/css/main.css',
  '/assets/js/api.js',
  '/assets/js/auth.js',
  '/assets/js/ui.js',
  '/components/layout.js',
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then(cache => cache.addAll(STATIC_ASSETS)).catch(() => {})
  );
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k)))
    )
  );
  self.clients.claim();
});

self.addEventListener('fetch', (event) => {
  // Only cache GET requests for same-origin static assets
  if (event.request.method !== 'GET') return;
  if (event.request.url.includes('/api/')) return; // Never cache API calls

  event.respondWith(
    caches.match(event.request).then(cached => {
      if (cached) return cached;
      return fetch(event.request).then(response => {
        if (response.ok && response.type === 'basic') {
          const clone = response.clone();
          caches.open(CACHE_NAME).then(cache => cache.put(event.request, clone));
        }
        return response;
      }).catch(() => cached || new Response('Offline', { status: 503 }));
    })
  );
});
