import { useEffect, useState } from 'react'
import Badge from './Badge'

// 약 하나의 DUR 배지 (A-5): "임부 금기", "용량 주의". 화면을 먼저 그리고 배지는 따로 불러 채워요
// 자료가 없거나 불러오지 못하면 아무것도 보여 주지 않아요 ("안전"처럼 보이는 표시도 하지 않아요)
function DurBadges({ itemSeq }) {
  const [state, setState] = useState({ seq: '', badges: [] })

  useEffect(() => {
    let alive = true
    fetch(`/api/drugs/${encodeURIComponent(itemSeq)}/dur`)
      .then(res => (res.ok ? res.json() : { badges: null }))
      .then(data => { if (alive) setState({ seq: itemSeq, badges: data.badges ?? [] }) })
      .catch(() => { if (alive) setState({ seq: itemSeq, badges: [] }) })
    return () => { alive = false }
  }, [itemSeq])

  if (state.seq !== itemSeq) return null
  return state.badges.map(b => (
    <Badge key={b.label} type={b.type}>DUR · {b.label}</Badge>
  ))
}
export default DurBadges
