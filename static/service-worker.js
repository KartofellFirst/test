self.addEventListener("install", (e) => {
  e.waitUntil(
    caches.open("nt-cache").then((cache) =>
      cache.addAll(["/", "/static/index.html",  "/static/icon-192.png", "/static/icon-512.png"])
    )
  );
});

self.addEventListener("fetch", (e) => {
  e.respondWith(
    caches.match(e.request).then((res) => res || fetch(e.request))
  );
});

// fallback?
self.addEventListener("fetch", (e) => {
  e.respondWith(
    caches.match(e.request).then((res) => {
      return res || fetch(e.request).catch(() => caches.match("/static/index.html"));
    })
  );
});
