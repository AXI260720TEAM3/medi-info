import { useEffect, useState } from 'react'
import { Link } from 'react-router'
import { formatDistance } from '../utils/pharmacy'

// 채팅에서 "약사와 상담하세요"가 나올 때 답변 아래에 붙는 상자 (REQ-F-050)
// 위치 권한을 이미 허용했으면 바로 가까운 문 연 약국 3곳, 아니면 버튼을 눌러야 찾아요 (갑자기 권한 창을 띄우지 않기)
const SHOW = 3

function OpenPharmacies() {
  const [state, setState] = useState({ step: 'idle', items: [], lat: '', lon: '', error: '' })

  const locate = () => {
    if (!navigator.geolocation) {
      setState(s => ({ ...s, step: 'error', error: '이 브라우저는 위치 찾기를 지원하지 않아요.' }))
      return
    }
    setState(s => ({ ...s, step: 'loading', error: '' }))
    navigator.geolocation.getCurrentPosition(
      async pos => {
        const lat = pos.coords.latitude.toFixed(5)
        const lon = pos.coords.longitude.toFixed(5)
        try {
          const res = await fetch(`/api/pharmacies/near?${new URLSearchParams({ lat, lon })}`)
          if (!res.ok) throw new Error()
          const data = await res.json()
          setState({ step: 'done', items: data.items.slice(0, SHOW), lat, lon, error: '' })
        } catch {
          setState(s => ({ ...s, step: 'error', error: '약국 정보를 불러오지 못했어요.' }))
        }
      },
      () => setState(s => ({ ...s, step: 'error', error: '위치를 알 수 없어요. 약국 화면에서 지역으로 찾아 주세요.' })),
      { timeout: 10000 },
    )
  }

  // 이미 허용한 사람은 바로 찾아요 (처음 한 번)
  useEffect(() => {
    if (!navigator.permissions) return
    navigator.permissions.query({ name: 'geolocation' })
      .then(status => { if (status.state === 'granted') locate() })
      .catch(() => {})
  }, [])

  const moreLink = state.lat ? `/pharmacy?${new URLSearchParams({ lat: state.lat, lon: state.lon })}` : '/pharmacy'

  return (
    <aside aria-label="지금 문 연 약국" style={{ marginTop: 10, padding: '10px 12px', borderRadius: 'var(--radius)', background: 'var(--surface-muted)', whiteSpace: 'normal' }}>
      <strong style={{ fontSize: 15 }}>지금 문 연 약국</strong>

      {state.step === 'idle' && (
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginTop: 6 }}>
          <button type="button" className="btn btn-secondary" onClick={locate}>내 위치로 찾기</button>
          <Link to="/pharmacy" className="btn btn-secondary">약국 화면으로</Link>
        </div>
      )}
      {state.step === 'loading' && <p className="muted" style={{ margin: '6px 0 0' }} role="status">가까운 약국을 찾는 중이에요</p>}
      {state.step === 'error' && <p className="muted" style={{ margin: '6px 0 0' }}>{state.error} <Link to="/pharmacy">약국 화면으로</Link></p>}

      {state.step === 'done' && (
        <>
          {state.items.length === 0 && <p className="muted" style={{ margin: '6px 0 0' }}>가까운 곳에 지금 영업 중인 약국이 없어요.</p>}
          <ul style={{ listStyle: 'none', margin: '6px 0 0', padding: 0, display: 'flex', flexDirection: 'column', gap: 6 }}>
            {state.items.map(p => (
              <li key={p.id} style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
                <span style={{ flex: '1 1 160px', minWidth: 0 }}>
                  <b>{p.name}</b> <span className="muted">{formatDistance(p.distance)} · {p.close_label}</span>
                </span>
                {p.tel && <a href={`tel:${p.tel}`} aria-label={`${p.name}에 전화 ${p.tel}`}>전화</a>}
              </li>
            ))}
          </ul>
          <Link to={moreLink} style={{ display: 'inline-block', marginTop: 6 }}>지도에서 더 보기</Link>
        </>
      )}
    </aside>
  )
}
export default OpenPharmacies
