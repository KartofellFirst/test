self.addEventListener("install", (e) => {
  e.waitUntil(
    caches.open("nt-cache").then((cache) =>
      cache.addAll([
        "/",
        "/static/index.html",
        "/static/fallback.html",
        "/static/icon-192.png",
        "/static/icon-512.png",
      ])
    )
  );
});

self.addEventListener("fetch", (e) => {
  if (e.request.url.includes("/static/din/")) return;
  e.respondWith(
    caches.match(e.request).then((res) => {
      return res || fetch(e.request).catch((err) =>
        caches.match("/static/fallback.html");
      );
    })
  );
});
