const CACHE = "missionlink-web-v4";
const ASSETS = ["./", "./index.html", "./styles.css", "./app.js", "./testbench.html", "./testbench.css", "./testbench.js", "./flasher.html", "./flasher.css", "./flasher.js", "./flasher-validate.js", "./manifest.webmanifest", "./icon.svg", "./assets/MissionLinkLogo.png"];
self.addEventListener("install", event => event.waitUntil(caches.open(CACHE).then(cache => cache.addAll(ASSETS))));
self.addEventListener("activate", event => event.waitUntil(caches.keys().then(keys => Promise.all(keys.filter(key => key !== CACHE).map(key => caches.delete(key))))));
self.addEventListener("fetch", event => {
  if (event.request.method !== "GET" || new URL(event.request.url).origin !== self.location.origin) return;
  event.respondWith(caches.match(event.request).then(cached => cached || fetch(event.request).then(response => {
    if (response.ok) { const copy = response.clone(); caches.open(CACHE).then(cache => cache.put(event.request, copy)); }
    return response;
  })));
});