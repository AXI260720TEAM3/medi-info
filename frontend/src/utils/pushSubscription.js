
const PUSH_DISABLED_KEY = 'yakbaro-push-disabled'

// VAPID 공개키 변환
function convertPublicKey(key) {
  const padding = '='.repeat((4 - key.length % 4) % 4)
  const base64 = (key + padding)
    .replace(/-/g, '+')
    .replace(/_/g, '/')

  return Uint8Array.from(
    atob(base64),
    char => char.charCodeAt(0)
  )
}

function checkPushSupport() {
  if (
    !('serviceWorker' in navigator) ||
    !('PushManager' in window) ||
    !('Notification' in window)
  ) {
    throw new Error('이 브라우저에서는 푸시 알림을 지원하지 않아요.')
  }
}

// 이 기기에서 사용자가 직접 알림을 껐는지 확인
export function isPushDisabled() {
  return localStorage.getItem(PUSH_DISABLED_KEY) === 'true'
}

// 기기 푸시 연결
export async function ensurePushSubscription(force = false) {
  checkPushSupport()

  if (!force && isPushDisabled()) {
    throw new Error(
      '이 기기 알림이 꺼져 있어요. 기기 알림을 켜고 저장해 주세요.'
    )
  }

  let permission = Notification.permission

  if (permission === 'default') {
    permission = await Notification.requestPermission()
  }

  if (permission !== 'granted') {
    throw new Error(
      '알림 권한이 차단되어 있어요. 브라우저에서 알림을 허용해 주세요.'
    )
  }

  const keyRes = await fetch('/api/push/public-key')

  if (!keyRes.ok) {
    throw new Error('푸시 공개키를 불러오지 못했어요.')
  }

  const { public_key } = await keyRes.json()
  const registration = await navigator.serviceWorker.ready

  let subscription = await registration.pushManager.getSubscription()

  if (!subscription) {
    subscription = await registration.pushManager.subscribe({
      userVisibleOnly: true,
      applicationServerKey: convertPublicKey(public_key),
    })
  }

  const res = await fetch('/api/push/subscribe', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(subscription.toJSON()),
  })

  if (!res.ok) {
    const data = await res.json().catch(() => ({}))

    throw new Error(
      typeof data.detail === 'string'
        ? data.detail
        : '푸시 알림 연결에 실패했어요.'
    )
  }

  localStorage.removeItem(PUSH_DISABLED_KEY)
}

// 이 기기 알림 끄기
export async function disableDevicePush() {
  checkPushSupport()

  const registration = await navigator.serviceWorker.ready
  const subscription = await registration.pushManager.getSubscription()

  if (subscription) {
    const res = await fetch('/api/push/subscribe', {
      method: 'DELETE',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        endpoint: subscription.endpoint,
      }),
    })

    if (!res.ok && res.status !== 404) {
      throw new Error('푸시 연결 해제에 실패했어요.')
    }

    const removed = await subscription.unsubscribe()

    if (!removed) {
      throw new Error('브라우저 푸시 연결을 해제하지 못했어요.')
    }
  }

  localStorage.setItem(PUSH_DISABLED_KEY, 'true')
}
