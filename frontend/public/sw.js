self.addEventListener('install', () => {
  self.skipWaiting()
})

self.addEventListener('activate', (event) => {
  event.waitUntil(self.clients.claim())
})

// 서버에서 푸시 알림이 도착했을 때
self.addEventListener('push', (event) => {
  event.waitUntil(
    self.registration.showNotification('약바로 복약 알림', {
      body: '설정한 복약 시간을 확인해 주세요.',
      icon: '/favicon.svg',
      data: {
        url: '/my-meds',
      },
    })
  )
})

// 사용자가 알림을 클릭했을 때
self.addEventListener('notificationclick', (event) => {
  event.notification.close()

  event.waitUntil(
    (async () => {
      const targetUrl = new URL(
        '/my-meds',
        self.location.origin
      ).href

      const windows = await self.clients.matchAll({
        type: 'window',
        includeUncontrolled: true,
      })

      for (const windowClient of windows) {
        if (
          new URL(windowClient.url).origin ===
          self.location.origin
        ) {
          const page = await windowClient.navigate(targetUrl)
          return (page || windowClient).focus()
        }
      }

      return self.clients.openWindow(targetUrl)
    })()
  )
})