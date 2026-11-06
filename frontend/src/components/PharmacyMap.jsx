import { useEffect, useRef } from 'react'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'

// 약국 지도 (Leaflet + OpenStreetMap, 키 필요 없음)
// 약국 화면은 이 입구만 알아요. 나중에 카카오 지도도 같은 입구로 만들 거예요
//   items: 약국 목록 (lat, lon, name, is_open)
//   start: 첫 핀 번호 (목록 번호와 같게. 2쪽이면 11)
//   myLat, myLon: 내 위치 (없으면 '')

const TILE = 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png'
const SEOUL = [37.5665, 126.978]   // 약국이 없을 때 처음 보여 줄 곳

// 번호 핀 (시안: 검은 동그라미 안에 흰 번호). 문 닫은 곳은 회색
function numberIcon(n, open) {
  const bg = open ? '#111827' : '#6B7280'
  return L.divIcon({
    className: '',
    html: `<span style="display:flex;align-items:center;justify-content:center;width:30px;height:30px;border-radius:15px;background:${bg};color:#fff;font:700 14px/1 'Noto Sans KR',sans-serif;border:2px solid #fff;box-shadow:0 1px 4px rgba(0,0,0,.35)">${n}</span>`,
    iconSize: [30, 30],
    iconAnchor: [15, 15],
  })
}

// 내 위치 (시안: 파란 점과 옅은 테두리)
const ME_ICON = L.divIcon({
  className: '',
  html: '<span style="display:block;width:20px;height:20px;border-radius:10px;background:#2563EB;border:4px solid #fff;box-shadow:0 0 0 8px rgba(37,99,235,.18)"></span>',
  iconSize: [20, 20],
  iconAnchor: [10, 10],
})

function PharmacyMap({ items, start = 1, myLat = '', myLon = '' }) {
  const boxRef = useRef(null)    // 지도를 그릴 div
  const mapRef = useRef(null)    // Leaflet 지도 (한 번만 만들어요)
  const layerRef = useRef(null)  // 핀을 모아 두는 층 (목록이 바뀌면 통째로 비워요)

  // 1) 처음 한 번: 지도 만들기. 화면을 떠나면 지도도 치워요
  useEffect(() => {
    const map = L.map(boxRef.current, { scrollWheelZoom: false }).setView(SEOUL, 13)
    L.tileLayer(TILE, { maxZoom: 19, attribution: '&copy; OpenStreetMap' }).addTo(map)
    layerRef.current = L.layerGroup().addTo(map)
    mapRef.current = map
    return () => map.remove()
  }, [])

  // 2) 목록이나 내 위치가 바뀔 때마다: 핀을 다시 찍고, 핀이 다 보이게 화면 맞추기
  useEffect(() => {
    const layer = layerRef.current
    layer.clearLayers()
    const points = []   // 화면 맞추기에 쓸 좌표들 [[위도, 경도], ...]

    items.forEach((p, i) => {
      if (!p.lat || !p.lon) return                 // 좌표가 없는 약국은 건너뛰기
      L.marker([Number(p.lat), Number(p.lon)], { icon: numberIcon(start + i, p.is_open), title: p.name }).addTo(layer)
      points.push([Number(p.lat), Number(p.lon)])
    })

    if (myLat && myLon) {
      L.marker([Number(myLat), Number(myLon)], { icon: ME_ICON, title: '내 위치' }).addTo(layer)
      points.push([Number(myLat), Number(myLon)])
    }
    if (points.length > 0) mapRef.current.fitBounds(points, { padding: [32, 32], maxZoom: 17 })
  }, [items, start, myLat, myLon])

  return (
    <div ref={boxRef} role="region" aria-label="약국 지도"
      style={{ width: '100%', height: '100%', minHeight: 320, borderRadius: 16, border: '1px solid var(--border)', zIndex: 0 }} />
  )
}
export default PharmacyMap
