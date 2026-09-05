const ICON = "/static/notifications/icons/icon-192.png";

self.addEventListener("install", () => self.skipWaiting());
self.addEventListener("activate", (event) => event.waitUntil(self.clients.claim()));

self.addEventListener("push", (event) => {
  let data = {
    title: "Django Web Push",
    body: "Yeni bir bildiriminiz var.",
    url: "/",
  };

  if (event.data) {
    try {
      data = { ...data, ...event.data.json() };
    } catch (_) {
      data.body = event.data.text();
    }
  }

  // Aynı tag = mevcut bildirimi değiştir. Her push için benzersiz tag kullan.
  // Backend notification_id gönderiyorsa kalıcı DB kaydı ile birebir eşleşir.
  const uniqueTag = data.tag || `notification-${data.notification_id || Date.now()}-${Math.random()}`;

  const options = {
    body: data.body,
    icon: ICON,
    badge: ICON,
    tag: uniqueTag,
    data: {
      url: data.url || "/",
      notificationId: data.notification_id || null,
    },
  };

  event.waitUntil(self.registration.showNotification(data.title, options));
});

self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  const targetUrl = new URL(event.notification.data?.url || "/", self.location.origin).href;

  event.waitUntil((async () => {
    const windows = await self.clients.matchAll({ type: "window", includeUncontrolled: true });
    for (const client of windows) {
      const clientOrigin = new URL(client.url).origin;
      if (clientOrigin === self.location.origin) {
        if ("navigate" in client) {
          await client.navigate(targetUrl);
        }
        if ("focus" in client) {
          return client.focus();
        }
      }
    }
    if (self.clients.openWindow) {
      return self.clients.openWindow(targetUrl);
    }
  })());
});
