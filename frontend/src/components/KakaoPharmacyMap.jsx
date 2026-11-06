import { useEffect, useRef } from 'react'
import { ME_HTML, SEOUL, pinHtml } from './mapPins'

// 약국 지도 (카카오맵). 입구는 PharmacyMap.jsx 설명을 보세요
// 카카오 SDK는 npm이 아니라 카카오 서버에서 <script>로 받아요. 한 번만 받게 Promise를 기억해 둬요
let sdkPromise = null

function loadKakao(appKey) {
  if (window.kakao?.maps?.LatLng) return Promise.resolve(window.kakao)
  if (sdkPromise) return sdkPromise
  sdkPromise = new Promise((resolve, reject) => {
    const script = document.createElement('script')
    script.src = `https://dapi.kakao.com/v2/maps/sdk.js?appkey=${encodeURIComponent(appKey)}&autoload=false`
    // 받기 실패: 키 오류, 등록 안 된 주소(도메인), 인터넷 끊김
    script.onerror = () => { sdkPromise = null; reject(new Error('카카오 지도를 불러오지 못했어요')) }
    script.onload = () => {
      if (!window.kakao?.maps) { sdkPromise = null; reject(new Error('카카오 지도 준비 실패')); return }
      window.kakao.maps.load(() => resolve(window.kakao))
    }
    document.head.appendChild(script)
  })
  return sdkPromise
}

// HTML 글자로 핀 칸(div)을 만들어요. 카카오 CustomOverlay는 칸을 받아서 지도 위에 올려요
function makePin(html, title, onClick) {
  const el = document.createElement('div')
  el.innerHTML = html
  if (title) el.title = title
  if (onClick) el.addEventListener('click', onClick)
  return el
}

function KakaoPharmacyMap({ appKey, onFail, items, start = 1, myLat = '', myLon = '', selectedId = null, onSelect = () => {} }) {
  const boxRef = useRef(null)
  const kakaoRef = useRef(null)     // 불러온 kakao (window.kakao)
  const mapRef = useRef(null)
  const overlaysRef = useRef([])    // 지금 지도에 올린 핀들 (목록이 바뀌면 다 내려요)
  const pinsRef = useRef({})        // 약국 id -> { overlay, n, open, name }
  const drawRef = useRef(() => {})  // 핀 다시 그리기 (SDK를 다 받은 뒤에도 부르려고 담아 둬요)
  const tilesRef = useRef(false)    // 지도 그림이 한 번이라도 그려졌는지
  const onSelectRef = useRef(onSelect)
  const onFailRef = useRef(onFail)

  useEffect(() => { onSelectRef.current = onSelect; onFailRef.current = onFail })

  // 1) 처음 한 번: SDK 받고 지도 만들기. 실패하면 약국 화면에 알려서 Leaflet으로 바꿔요
  //    등록 안 된 주소면 SDK는 받아져도 지도 그림이 안 올 수 있어서, 5초 안에 안 그려지면 실패로 봐요
  useEffect(() => {
    let alive = true
    let timer = null
    loadKakao(appKey)
      .then(kakao => {
        if (!alive) return
        kakaoRef.current = kakao
        const map = new kakao.maps.Map(boxRef.current, { center: new kakao.maps.LatLng(...SEOUL), level: 4 })
        map.addControl(new kakao.maps.ZoomControl(), kakao.maps.ControlPosition.RIGHT)   // Leaflet처럼 +/- 버튼
        mapRef.current = map
        kakao.maps.event.addListener(map, 'tilesloaded', () => { tilesRef.current = true })
        timer = setTimeout(() => { if (alive && !tilesRef.current) onFailRef.current?.() }, 5000)
        drawRef.current()
      })
      .catch(() => { if (alive) onFailRef.current?.() })
    return () => { alive = false; clearTimeout(timer) }
  }, [appKey])

  // 2) 목록이나 내 위치가 바뀌면: 핀을 다시 올리고, 다 보이게 맞추기
  useEffect(() => {
    drawRef.current = () => {
      const kakao = kakaoRef.current
      const map = mapRef.current
      if (!kakao || !map) return    // 아직 SDK를 받는 중이면, 받은 뒤에 1)에서 다시 불러요
      overlaysRef.current.forEach(o => o.setMap(null))
      overlaysRef.current = []
      pinsRef.current = {}
      const bounds = new kakao.maps.LatLngBounds()
      let count = 0

      items.forEach((p, i) => {
        if (!p.lat || !p.lon) return
        const pos = new kakao.maps.LatLng(Number(p.lat), Number(p.lon))
        const n = start + i
        const content = makePin(pinHtml(n, p.is_open), p.name, () => onSelectRef.current(p.id))
        const overlay = new kakao.maps.CustomOverlay({ position: pos, content, yAnchor: 0.5, clickable: true, zIndex: 2 })
        overlay.setMap(map)
        overlaysRef.current.push(overlay)
        pinsRef.current[p.id] = { overlay, n, open: p.is_open, name: p.name }
        bounds.extend(pos)
        count++
      })

      if (myLat && myLon) {
        const pos = new kakao.maps.LatLng(Number(myLat), Number(myLon))
        const overlay = new kakao.maps.CustomOverlay({ position: pos, content: makePin(ME_HTML, '내 위치'), yAnchor: 0.5, zIndex: 1 })
        overlay.setMap(map)
        overlaysRef.current.push(overlay)
        bounds.extend(pos)
        count++
      }
      if (count > 0) map.setBounds(bounds, 40, 40, 40, 40)
    }
    drawRef.current()
  }, [items, start, myLat, myLon])

  // 3) 고른 약국이 바뀌면: 그 핀만 파랗게, 지도 가운데로 (다시 맞추지 않아요)
  useEffect(() => {
    Object.entries(pinsRef.current).forEach(([id, { overlay, n, open, name }]) => {
      const picked = id === String(selectedId)
      overlay.setContent(makePin(pinHtml(n, open, picked), name, () => onSelectRef.current(id)))
      overlay.setZIndex(picked ? 10 : 2)
    })
    const picked = pinsRef.current[selectedId]
    if (picked && mapRef.current) mapRef.current.panTo(picked.overlay.getPosition())
  }, [selectedId, items])

  return (
    <div ref={boxRef} role="region" aria-label="약국 지도"
      style={{ width: '100%', height: '100%', minHeight: 320, borderRadius: 16, border: '1px solid var(--border)', overflow: 'hidden' }} />
  )
}
export default KakaoPharmacyMap
