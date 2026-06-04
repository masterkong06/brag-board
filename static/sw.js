self.addEventListener('install', () => self.skipWaiting());
self.addEventListener('activate', (e) => e.waitUntil(self.clients.claim()));

self.addEventListener('push', function(event) {
  console.log('[SW] Push received:', event.data ? event.data.text() : 'no data');
  let data = {};
  try { data = event.data.json(); } catch(e) { data = { title: 'Brag Board', body: event.data ? event.data.text() : 'New activity!' }; }
  event.waitUntil(
    self.registration.showNotification(data.title || 'Brag Board', {
      body: data.body || '',
      icon: '/static/icons/icon-192.png',
      badge: '/static/icons/icon-192.png',
      tag: 'brag-push',
      renotify: true,
    }).then(() => console.log('[SW] Notification shown'))
      .catch(err => console.error('[SW] showNotification failed:', err))
  );
});

self.addEventListener('notificationclick', function(event) {
  event.notification.close();
  event.waitUntil(clients.openWindow('/'));
});
