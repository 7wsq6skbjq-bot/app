// Portech PWA — minimal service worker.
// We register it for the offline shell + Add-to-Home-Screen install criteria.
// We deliberately keep caching strategy minimal so admin data stays fresh.

const CACHE = "portech-shell-v1";

const PRECACHE = [
    "/",
    "/manifest.json",
    "/icon-192.png",
    "/icon-512.png",
    "/apple-touch-icon.png",
];

self.addEventListener("install", (event) => {
    event.waitUntil(
        caches.open(CACHE).then((cache) => cache.addAll(PRECACHE).catch(() => {})),
    );
    self.skipWaiting();
});

self.addEventListener("activate", (event) => {
    event.waitUntil(
        caches.keys().then((keys) =>
            Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))),
        ),
    );
    self.clients.claim();
});

// Network-first for everything (so admin data is fresh), fallback to cache
// only if offline. Skip API requests so authentication & writes always go
// straight to the network.
self.addEventListener("fetch", (event) => {
    const req = event.request;
    const url = new URL(req.url);

    // Never intercept API calls — always live network.
    if (url.pathname.startsWith("/api/")) return;

    // Only handle GET requests.
    if (req.method !== "GET") return;

    event.respondWith(
        fetch(req)
            .then((resp) => {
                // Cache successful navigations and static assets in background.
                if (
                    resp.ok &&
                    (req.mode === "navigate" || url.pathname.startsWith("/static/"))
                ) {
                    const clone = resp.clone();
                    caches.open(CACHE).then((cache) => cache.put(req, clone));
                }
                return resp;
            })
            .catch(() => caches.match(req).then((cached) => cached || caches.match("/"))),
    );
});
