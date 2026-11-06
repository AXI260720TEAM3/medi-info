import { useEffect, useState } from 'react'
import { useSearchParams } from 'react-router'
import Loading from '../components/Loading'
import ErrorMessage from '../components/ErrorMessage'
import AlertBox from '../components/AlertBox'
import Badge from '../components/Badge'

const PAGE_SIZE = 10
const SIDO = [
  '서울특별시', '부산광역시', '대구광역시', '인천광역시', '광주광역시', '대전광역시', '울산광역시', '세종특별자치시',
  '경기도', '강원특별자치도', '충청북도', '충청남도', '전북특별자치도', '전라남도', '경상북도', '경상남도', '제주특별자치도',
]

const COLUMN = { display: 'flex', flexDirection: 'column', gap: 16 }

// 카카오맵에 약국 위치를 핀으로 띄우는 주소 (지도 키가 필요 없어요)
const mapLink = p => `https://map.kakao.com/link/map/${encodeURIComponent(p.name)},${p.lat},${p.lon}`

// 위치 API가 주는 거리(km 글자, 예: "0.12")를 사람이 읽기 쉬운 글자로
function formatDistance(km) {
  const n = Number(km)
  if (n < 1) return `${Math.round(n * 1000)}m`
  return `${n.toFixed(1)}km`
}

// 위치를 못 받았을 때 보여 줄 말 (브라우저가 주는 오류 번호별)
const GEO_ERROR = {
  1: '위치 권한이 꺼져 있어요. 브라우저 설정에서 허용하거나 아래에서 지역으로 찾아 주세요.',
  2: '지금 위치를 알 수 없어요. 아래에서 지역으로 찾아 주세요.',
  3: '위치를 찾는 데 너무 오래 걸려요. 다시 눌러 보거나 지역으로 찾아 주세요.',
}

function Pharmacy() {
  const [searchParams, setSearchParams] = useSearchParams()
  const sido = searchParams.get('sido') ?? ''
  const sigungu = searchParams.get('sigungu') ?? ''
  const lat = searchParams.get('lat') ?? ''
  const lon = searchParams.get('lon') ?? ''
  const page = Math.max(1, Number(searchParams.get('page')) || 1)
  const near = lat !== '' && lon !== ''   // 주소에 좌표가 있으면 '내 주변' 검색
  const key = near ? `near|${lat}|${lon}` : `${sido}|${sigungu}|${page}`

  const [form, setForm] = useState({ sido: sido || SIDO[0], sigungu })
  const [answer, setAnswer] = useState({ key: '', total: 0, items: [], error: '' })
  const [retry, setRetry] = useState(0)
  const [geo, setGeo] = useState({ busy: false, error: '' })
  const ready = near || (sido !== '' && sigungu !== '')
  const loading = ready && answer.key !== key
  const totalPages = Math.ceil(answer.total / PAGE_SIZE)

  useEffect(() => {
    if (!ready) return
    const url = near
      ? `/api/pharmacies/near?${new URLSearchParams({ lat, lon })}`
      : `/api/pharmacies?${new URLSearchParams({ sido, sigungu, page: String(page) })}`
    fetch(url)
      .then(async res => {
        const data = await res.json().catch(() => ({}))
        if (!res.ok) throw new Error(typeof data.detail === 'string' ? data.detail : '약국을 찾지 못했어요. 잠시 후 다시 시도해 주세요.')
        setAnswer({ key, total: data.total, items: data.items, error: '' })
      })
      .catch(err => setAnswer({ key, total: 0, items: [], error: err.message }))
  }, [ready, near, lat, lon, sido, sigungu, page, key, retry])

  // 브라우저에 지금 위치를 물어봐요. https나 localhost에서만 돼요
  const handleNear = () => {
    if (!navigator.geolocation) {
      setGeo({ busy: false, error: '이 브라우저는 위치 찾기를 지원하지 않아요. 아래에서 지역으로 찾아 주세요.' })
      return
    }
    setGeo({ busy: true, error: '' })
    navigator.geolocation.getCurrentPosition(
      pos => {
        setGeo({ busy: false, error: '' })
        setSearchParams({ lat: pos.coords.latitude.toFixed(5), lon: pos.coords.longitude.toFixed(5) })
      },
      err => setGeo({ busy: false, error: GEO_ERROR[err.code] ?? GEO_ERROR[2] }),
      { timeout: 10000 },
    )
  }

  const handleSearch = e => {
    e.preventDefault()
    if (form.sigungu.trim() === '') return
    setSearchParams({ sido: form.sido, sigungu: form.sigungu.trim() })   // 새 검색은 1쪽부터
  }

  const goPage = p => {
    setSearchParams({ sido, sigungu, page: String(p) })
    window.scrollTo(0, 0)
  }

  const showResult = ready && !loading && !answer.error

  return (
    <div style={COLUMN}>
      <h1 className="title">약국 찾기</h1>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
        <button type="button" className="btn btn-primary" style={{ minHeight: 52, fontSize: 18 }} onClick={handleNear} disabled={geo.busy || loading}>
          {geo.busy ? '위치를 찾는 중이에요' : '내 주변 약국 찾기'}
        </button>
        {geo.error && <p role="alert" style={{ margin: 0, color: 'var(--text)' }}>{geo.error}</p>}
      </div>

      <form className="card" style={{ display: 'flex', flexWrap: 'wrap', gap: 8, padding: 16, borderRadius: 16 }} onSubmit={handleSearch}>
        <label htmlFor="sido" className="muted" style={{ alignSelf: 'center' }}>시/도</label>
        <select id="sido" className="input" style={{ flex: '1 1 160px', minHeight: 48, fontSize: 17 }}
          value={form.sido} onChange={e => setForm({ ...form, sido: e.target.value })}>
          {SIDO.map(s => <option key={s} value={s}>{s}</option>)}
        </select>
        <label htmlFor="sigungu" className="muted" style={{ alignSelf: 'center' }}>시/군/구</label>
        <input id="sigungu" className="input" style={{ flex: '1 1 160px', minWidth: 0, minHeight: 48, fontSize: 17 }}
          placeholder="예: 중구, 수원시"
          value={form.sigungu} onChange={e => setForm({ ...form, sigungu: e.target.value })} />
        <button type="submit" className="btn btn-primary" style={{ minHeight: 48, padding: '0 24px' }} disabled={loading}>찾기</button>
      </form>

      {!ready && <p className="muted" style={{ margin: 0 }}>내 주변 약국을 찾거나, 시/도를 고르고 시/군/구를 적어 주세요.</p>}
      {loading && <Loading text="약국을 찾는 중이에요" />}
      {ready && !loading && answer.error && <ErrorMessage message={answer.error} onRetry={() => setRetry(r => r + 1)} />}

      {showResult && (
        <p style={{ margin: 0, color: 'var(--text-muted)' }}>
          {near
            ? <><strong style={{ color: 'var(--text)' }}>내 위치</strong>에서 가까운 약국 {answer.total}곳</>
            : <><strong style={{ color: 'var(--text)' }}>{sido} {sigungu}</strong> 약국 {answer.total}곳</>}
          {totalPages > 1 && ` · ${page} / ${totalPages}쪽`}
        </p>
      )}

      {showResult && answer.total === 0 && (
        <AlertBox type="info" title="약국을 찾지 못했어요">
          <p>{near ? '가까운 곳에 약국 정보가 없어요. 지역으로 찾아 주세요.' : '시/군/구 이름을 다시 확인해 주세요. 예: "중구", "수원시 장안구"'}</p>
        </AlertBox>
      )}

      {showResult && answer.total > 0 && (
        <AlertBox type="info" title="가기 전에 전화로 확인하세요">
          <p>영업시간은 약국이 신고한 정보예요. 공휴일이나 사정에 따라 다를 수 있어요.</p>
        </AlertBox>
      )}

      {showResult && answer.items.length > 0 && (
        <section aria-label="약국 목록" style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          {answer.items.map(p => (
            <article key={p.id} className="card" style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: 16 }}>
              <div style={{ flex: '1 1 240px', minWidth: 0, display: 'flex', flexDirection: 'column', gap: 4 }}>
                <span className="card-title" style={{ overflowWrap: 'anywhere' }}>{p.name}</span>
                <span className="muted" style={{ overflowWrap: 'anywhere' }}>{p.addr}</span>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                  {p.distance && <Badge type="notice">{formatDistance(p.distance)}</Badge>}
                  {p.today_hours
                    ? <Badge type="notice">오늘 {p.today_hours}</Badge>
                    : <Badge type="none">오늘 쉬어요</Badge>}
                </div>
              </div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                {p.tel && <a href={`tel:${p.tel}`} className="btn btn-secondary">전화 {p.tel}</a>}
                {p.lat && p.lon && <a href={mapLink(p)} target="_blank" rel="noreferrer" className="btn btn-secondary">지도</a>}
              </div>
            </article>
          ))}
        </section>
      )}

      {showResult && totalPages > 1 && (
        <nav style={{ display: 'flex', justifyContent: 'center', gap: 6 }} aria-label="약국 목록 쪽">
          <button type="button" className="btn btn-secondary" onClick={() => goPage(page - 1)} disabled={page <= 1}>이전</button>
          <button type="button" className="btn btn-secondary" onClick={() => goPage(page + 1)} disabled={page >= totalPages}>다음</button>
        </nav>
      )}
    </div>
  )
}
export default Pharmacy
