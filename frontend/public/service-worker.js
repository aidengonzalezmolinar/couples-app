/* eslint-disable no-restricted-globals */

self.addEventListener('push', (event) => {
  let data = {};
  if (event.data) {
    try {
      data = event.data.json();
    } catch (e) {
      data = { title: 'New notification', body: event.data.text() };
    }
  }

  const title = data.title || 'New notification';
  const options = {
    body: data.body || '',
    icon: data.icon || '/logo192.png',
    badge: data.badge || '/logo192.png',
    data: {
      url: data.url || '/',
      notificationId: data.notificationId,
      ...data.extra,
    },
    tag: data.tag || undefined,
    renotify: data.renotify || false,
  };

  event.waitUntil(self.registration.showNotification(title, options));
});

self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  const targetUrl = event.notification.data?.url || '/';

  event.waitUntil(
    self.clients.matchAll({ type: 'window', includeUncontrolled: true }).then((clients) => {
      if (clients.length > 0) {
        const client = clients[0];
        client.focus();
        client.postMessage({ type: 'NOTIFICATION_CLICKED', url: targetUrl });
        return;
      }
      return self.clients.openWindow(targetUrl);
    })
  );
});

self.addEventListener('install', (event) => {
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(self.clients.claim());
});
