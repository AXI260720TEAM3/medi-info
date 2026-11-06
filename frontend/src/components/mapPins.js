// 지도 핀 모양 (Leaflet, 카카오 지도가 함께 써요. 같은 모양이어야 지도를 바꿔도 화면이 같아요)

// 번호 핀 (시안: 검은 동그라미 안에 흰 번호). 문 닫은 곳은 회색, 고른 약국은 파랗고 크게
export function pinSize(selected) {
  return selected ? 38 : 30
}

export function pinHtml(n, open, selected = false) {
  const bg = selected ? '#2563EB' : open ? '#111827' : '#6B7280'
  const size = pinSize(selected)
  return `<span style="display:flex;align-items:center;justify-content:center;width:${size}px;height:${size}px;border-radius:50%;background:${bg};color:#fff;font:700 ${selected ? 16 : 14}px/1 'Noto Sans KR',sans-serif;border:2px solid #fff;box-shadow:0 1px 4px rgba(0,0,0,.35);cursor:pointer">${n}</span>`
}

// 내 위치 (시안: 파란 점과 옅은 테두리)
export const ME_HTML = '<span style="display:block;width:20px;height:20px;border-radius:10px;background:#2563EB;border:4px solid #fff;box-shadow:0 0 0 8px rgba(37,99,235,.18)"></span>'

export const SEOUL = [37.5665, 126.978]   // 약국이 없을 때 처음 보여 줄 곳
