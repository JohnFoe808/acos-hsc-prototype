const CACHE = "acos-shell-v1";
const ASSETS = ["/", "/static/styles.css", "/static/app.js", "/manifest.webmanifest"];
self.addEventListener("install", event => event.waitUntil(caches.open(CACHE).then(cache => cache.addAll(ASSETS))));
self.addEventListener("activate", event => event.waitUntil(self.clients.claim()));
self.addEventListener("fetch", event => {
  if (event.request.method !== "GET" || event.request.url.includes("/api/")) return;
  event.respondWith(caches.match(event.request).then(hit => hit || fetch(event.request)));
});
