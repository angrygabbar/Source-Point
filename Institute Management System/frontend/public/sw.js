/* Institute Management service worker: caches static assets, never API responses or personal data. */
const CACHE = "institute-management-static-v1";
const BASE_PATH = new URL(self.registration.scope).pathname.replace(/\/$/, "");
const withBase = (path) => `${BASE_PATH}${path}`;
const OFFLINE_URL = withBase("/offline.html");

self.addEventListener("install", (event) => {
  event.waitUntil(caches.open(CACHE).then((c) => c.addAll([OFFLINE_URL, withBase("/icon.svg"), withBase("/manifest.webmanifest")])));
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k)))).then(() => self.clients.claim()),
  );
});

self.addEventListener("fetch", (event) => {
  const req = event.request;
  const url = new URL(req.url);
  if (req.method !== "GET" || url.origin !== self.location.origin || url.pathname.startsWith("/api/") || url.pathname.startsWith("/institute-api/")) return;
  if (url.pathname.startsWith(withBase("/_next/static/")) || url.pathname.endsWith(".svg") || url.pathname.endsWith(".webmanifest")) {
    event.respondWith(
      caches.match(req).then((hit) => hit || fetch(req).then((res) => {
        const copy = res.clone();
        if (res.ok) caches.open(CACHE).then((c) => c.put(req, copy));
        return res;
      })),
    );
    return;
  }
  if (req.mode === "navigate") {
    event.respondWith(fetch(req).catch(() => caches.match(OFFLINE_URL)));
  }
});

self.addEventListener("push", (event) => {
  let data = { title: "Institute Management System", body: "", url: withBase("/notifications") };
  try { data = { ...data, ...event.data.json() }; } catch (e) { /* plain payload */ }
  const target = data.url.startsWith("/") && !data.url.startsWith(`${BASE_PATH}/`) ? withBase(data.url) : data.url;
  event.waitUntil(self.registration.showNotification(data.title, { body: data.body, icon: withBase("/icon.svg"), data: { url: target } }));
});

self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  const url = (event.notification.data && event.notification.data.url) || withBase("/notifications");
  event.waitUntil(self.clients.matchAll({ type: "window" }).then((list) => {
    for (const c of list) if ("focus" in c) { c.navigate(url); return c.focus(); }
    return self.clients.openWindow(url);
  }));
});
