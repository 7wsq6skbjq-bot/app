// Portech PWA — minimal service worker.
// We register it for the offline shell + Add-to-Home-Screen install criteria.
// We deliberately keep caching strategy minimal so admin data stays fresh.
//
// CACHE VERSION: bump this on every deploy that changes navigation, layout, or
// any HTML/CSS pinned by the install step — forces all installed PWAs to
// purge their old cache and reload the current shell on next launch.

const CACHE = "portech-shell-v5";

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

// Allow the page (UpdatePrompt component) to ask us to swap in immediately
// instead of waiting until all tabs are closed.
self.addEventListener("message", (event) => {
    if (event.data && event.data.type === "SKIP_WAITING") {
        self.skipWaiting();
    }
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

// ── Web Push notifications ────────────────────────────────────────────────
self.addEventListener("push", (event) => {
    let data = {};
    try { data = event.data ? event.data.json() : {}; } catch (_e) { /* ignore */ }
    const title = data.title || "Portech";
    const options = {
        body: data.body || "",
        icon: "/icon-192.png",
        badge: "/icon-96.png",
        tag: data.tag || "portech",
        renotify: true,
        data: { url: data.url || "/adjointe" },
    };
    event.waitUntil(self.registration.showNotification(title, options));
});

self.addEventListener("notificationclick", (event) => {
    event.notification.close();
    const target = new URL(event.notification.data?.url || "/adjointe", self.location.origin).href;
    event.waitUntil((async () => {
        const wins = await self.clients.matchAll({ type: "window", includeUncontrolled: true });
        for (const client of wins) {
            if ("focus" in client) {
                await client.focus();
                if ("navigate" in client && client.url !== target) {
                    try { await client.navigate(target); } catch (_e) { /* ignore */ }
                }
                return;
            }
        }
        await self.clients.openWindow(target);
    })());
});
