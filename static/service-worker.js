/**
 * EnviroLearn Service Worker
 * ─────────────────────────
 * Strategy:
 *   - Static assets  → Cache-first (images, CSS, JS)
 *   - Flask routes   → Network-first (HTML pages, API)
 *   - Offline        → /offline fallback for uncached pages
 *   - Videos         → NOT cached (too large for browser cache)
 */

const CACHE_NAME    = 'envirolearn-v1';
const OFFLINE_URL   = '/offline';

// Assets to pre-cache on install
const PRECACHE_URLS = [
    '/',
    '/offline',
    '/static/logo.png',
    '/static/bg1.png',
    '/static/bg2.png',
    '/static/bg3.png',
    '/static/back.jpeg',
    '/static/games.png',
    '/static/badges.png',
    '/static/actions.png',
    '/static/quizzes.png',
    '/static/videos.png',
    '/static/challenges.png',
    '/static/leaderboard.png',
    '/static/gamebg.png',
    '/static/manifest.json',
];

// ── Install: pre-cache essential assets ──────────────────────────
self.addEventListener('install', event => {
    event.waitUntil(
        caches.open(CACHE_NAME)
            .then(cache => cache.addAll(PRECACHE_URLS))
            .then(() => self.skipWaiting())
    );
});

// ── Activate: clean up old caches ────────────────────────────────
self.addEventListener('activate', event => {
    event.waitUntil(
        caches.keys().then(keys =>
            Promise.all(
                keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k))
            )
        ).then(() => self.clients.claim())
    );
});

// ── Fetch: routing strategy ───────────────────────────────────────
self.addEventListener('fetch', event => {
    const url = new URL(event.request.url);

    // Skip non-GET and cross-origin requests
    if (event.request.method !== 'GET') return;
    if (url.origin !== location.origin)  return;

    // Skip large video files — never cache
    if (url.pathname.endsWith('.mp4')) return;

    // Static assets → Cache-first
    if (url.pathname.startsWith('/static/')) {
        event.respondWith(cacheFirst(event.request));
        return;
    }

    // API endpoints → Network-only (no cache)
    if (url.pathname.startsWith('/api/')) {
        event.respondWith(fetch(event.request));
        return;
    }

    // All other Flask routes → Network-first with offline fallback
    event.respondWith(networkFirstWithFallback(event.request));
});

// ── Cache-first strategy ──────────────────────────────────────────
async function cacheFirst(request) {
    const cached = await caches.match(request);
    if (cached) return cached;
    try {
        const response = await fetch(request);
        if (response.ok) {
            const cache = await caches.open(CACHE_NAME);
            cache.put(request, response.clone());
        }
        return response;
    } catch {
        return new Response('Asset unavailable offline', { status: 503 });
    }
}

// ── Network-first with offline fallback ──────────────────────────
async function networkFirstWithFallback(request) {
    try {
        const response = await fetch(request);
        if (response.ok) {
            const cache = await caches.open(CACHE_NAME);
            cache.put(request, response.clone());
        }
        return response;
    } catch {
        const cached = await caches.match(request);
        if (cached) return cached;
        // Show offline page
        const offlinePage = await caches.match(OFFLINE_URL);
        return offlinePage || new Response('<h1>You are offline</h1>', {
            headers: { 'Content-Type': 'text/html' }
        });
    }
}
