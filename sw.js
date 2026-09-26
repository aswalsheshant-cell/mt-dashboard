const CACHE_NAME = 'mt-dashboard-v1.4.0';
const SHELL_ASSETS = [
  'mobile.html',
  'index.html',
  'manifest.json',
  'monthly-insights.css',
  'chart.umd.js',
  'html2canvas.min.js',
  'jspdf.umd.min.js',
  'xlsx.core.min.js'
];

// Install: cache shell assets
self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME).then(cache => {
      return Promise.all(
        SHELL_ASSETS.map(asset => {
          return cache.add(asset).catch(e => {
            console.log(`Failed to cache ${asset}:`, e);
            // Non-critical assets, don't fail the entire install
          });
        })
      );
    }).then(() => self.skipWaiting())
  );
});

// Activate: clean old caches
self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(cacheNames => {
      return Promise.all(
        cacheNames.map(cacheName => {
          if (cacheName !== CACHE_NAME) {
            return caches.delete(cacheName);
          }
        })
      );
    }).then(() => self.clients.claim())
  );
});

// Fetch: dual strategy
// - Cache-First for shell assets (fast offline experience)
// - Network-First for data.js (always try fresh data)
self.addEventListener('fetch', event => {
  const { request } = event;
  const url = new URL(request.url);

  // Skip non-GET or cross-origin requests
  if (request.method !== 'GET' || url.origin !== self.location.origin) {
    return;
  }

  // data.js: Network-First (always try to get fresh, fallback to cached)
  if (url.pathname.endsWith('data.js')) {
    event.respondWith(
      fetch(request)
        .then(response => {
          // Cache successful response
          if (response && response.status === 200) {
            const responseClone = response.clone();
            caches.open(CACHE_NAME).then(cache => {
              cache.put(request, responseClone);
            });
          }
          return response;
        })
        .catch(e => {
          // Network failed, try cache
          return caches.match(request).then(cached => {
            if (cached) {
              return cached;
            }
            // Neither network nor cache available
            return new Response('Data temporarily unavailable. Please check your connection.', {
              status: 503,
              statusText: 'Service Unavailable'
            });
          });
        })
    );
    return;
  }

  // Shell assets: Cache-First (fast, offline)
  if (SHELL_ASSETS.some(asset => url.pathname.endsWith(asset))) {
    event.respondWith(
      caches.match(request)
        .then(cached => {
          if (cached) {
            return cached;
          }
          return fetch(request)
            .then(response => {
              if (response && response.status === 200) {
                const responseClone = response.clone();
                caches.open(CACHE_NAME).then(cache => {
                  cache.put(request, responseClone);
                });
              }
              return response;
            })
            .catch(() => {
              return new Response('Resource not available offline.', {
                status: 503,
                statusText: 'Service Unavailable'
              });
            });
        })
    );
    return;
  }

  // Everything else: Network-First (default)
  event.respondWith(
    fetch(request)
      .then(response => {
        if (response && response.status === 200) {
          const responseClone = response.clone();
          caches.open(CACHE_NAME).then(cache => {
            cache.put(request, responseClone);
          });
        }
        return response;
      })
      .catch(() => {
        return caches.match(request).catch(() => {
          return new Response('Network request failed.', {
            status: 503,
            statusText: 'Service Unavailable'
          });
        });
      })
  );
});

// Background sync (optional — for future queue/sync logic)
self.addEventListener('sync', event => {
  if (event.tag === 'sync-metrics') {
    event.waitUntil(
      // Placeholder: add sync logic here if needed
      Promise.resolve()
    );
  }
});
