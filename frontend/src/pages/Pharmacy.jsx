import { useEffect, useState } from 'react'
import { useSearchParams } from 'react-router'
import Loading from '../components/Loading'
import ErrorMessage from '../components/ErrorMessage'
import AlertBox from '../components/AlertBox'
import { SIDO, SIGUNGU } from '../data/sigungu'

const PAGE_SIZE = 10

const COLUMN = { display: 'flex', flexDirection: 'column', gap: 16 }

// 카카오맵에 약국 위치를 핀으로 띄우는 주소 (지도 키가 필요 없어요)
const mapLink = p => `https://map.kakao.com/link/map/${encodeURIComponent(p.name)},${p.lat},${p.lon}`

// 위치 API가 주는 거리(km 글자, 예: "0.12")를 사람이 읽기 쉬운 글자로
function formatDistance(km) {
  const n = Number(km)
  if (n < 1) return `${Math.round(n * 1000)}m`
  return `${n.toFixed(1)}km`
}

// 카드 둘째 줄 (시안: "350m · 오늘 23:00까지"). 지역 검색은 거리가 없어요
// 영업 중:          "70m · 오늘 23:00까지"
// 오늘 하는데 닫힘: "120m · 지금 영업 안 함 · 오늘 09:00~19:00"
// 오늘 쉼:          "300m · 오늘 쉬어요"
function infoLine(p) {
  let state
  if (p.is_open) state = p.close_label
  else if (p.today_hours) state = `지금 영업 안 함 · 오늘 ${p.today_hours}`
  else state = '오늘 쉬어요'

  if (p.distance) return `${formatDistance(p.distance)} · ${state}`
  return state
}

// "금요일 22:40" (시안의 기준 시각 줄)
const DAYS = ['일요일', '월요일', '화요일', '수요일', '목요일', '금요일', '토요일']
function nowLabel() {
  const d = new Date()
  return `${DAYS[d.getDay()]} ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
}

const TOOL = { minHeight: 44, display: 'flex', alignItems: 'center', gap: 6, padding: '0 14px', fontSize: 15 }
const HIDDEN = { position: 'absolute', width: 1, height: 1, overflow: 'hidden', clip: 'rect(0 0 0 0)' }
const NUMBER = { width: 30, height: 30, flex: 'none', borderRadius: 15, background: 'var(--text)', color: '#FFFFFF', fontSize: 14, fontWeight: 700, display: 'flex', alignItems: 'center', justifyContent: 'center' }
const CARD = { display: 'flex', alignItems: 'center', gap: 12, padding: 16 }
// 시/도의 시/군/구 목록. '전국'('')처럼 목록에 없는 시/도면 빈 목록
const sigunguOf = sido => SIGUNGU[sido] ?? []

// 주소에서 검색 칸에 넣을 시/도·시/군/구를 꺼내요. 우리 목록에 없으면 null
//   "경기도 성남시 수정구 수정로 1"  -> { sido: '경기도', sigungu: '성남시' }
//   "세종특별자치시 한누리대로 2130" -> { sido: '세종특별자치시', sigungu: '' }
//   "충청남도 없는군 ..."             -> null
function regionOf(addr) {
  const [sido, second] = addr.split(' ')
  const list = SIGUNGU[sido]

  if (!list) return null
  if (list.length === 0) return {sido, sigungu: ""}
  if (list.includes(second)) return {sido, sigungu: second}
  return null
}

const ICON_BTN = { width: 44, height: 44, flex: 'none', borderRadius: 12, background: 'var(--primary-bg)', color: 'var(--primary-text)', display: 'flex', alignItems: 'center', justifyContent: 'center' }

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
  const name = searchParams.get('name') ?? ''      // 약국 이름 검색
  const showAll = searchParams.get('all') === '1'   // 문 닫은 곳도 보기
  const key = (near ? `near|${lat}|${lon}` : `${sido}|${sigungu}|${name}|${page}`) + `|${showAll}`

  // 이름 검색은 시/도 없이(전국) 찾을 수 있어서 주소에 sido가 빈 채로 올 수 있어요
  const firstSido = searchParams.has('sido') ? sido : SIDO[0]
  const [form, setForm] = useState({ sido: firstSido, sigungu: sigungu || (sigunguOf(firstSido)[0] ?? ''), name })
  const [answer, setAnswer] = useState({ key: '', total: 0, items: [], error: '' })
  const [retry, setRetry] = useState(0)
  const [geo, setGeo] = useState({ busy: false, error: '' })
  const noSigungu = SIGUNGU[sido]?.length === 0      // 세종처럼 시/군/구가 없는 곳
  const ready = near || name !== '' || (sido !== '' && (sigungu !== '' || noSigungu))
  const loading = ready && answer.key !== key
  const totalPages = Math.ceil(answer.total / PAGE_SIZE)

  useEffect(() => {
    if (!ready) return
    const open_now = String(!showAll && name === '')   // 이름 검색은 닫은 곳도 보여 줘요 (문 연 곳이 위로)
    const url = near
      ? `/api/pharmacies/near?${new URLSearchParams({ lat, lon, open_now })}`
      : `/api/pharmacies?${new URLSearchParams({ sido, sigungu, name, page: String(page), open_now })}`
    fetch(url)
      .then(async res => {
        const data = await res.json().catch(() => ({}))
        if (!res.ok) throw new Error(typeof data.detail === 'string' ? data.detail : '약국을 찾지 못했어요. 잠시 후 다시 시도해 주세요.')
        setAnswer({ key, total: data.total, items: data.items, error: '' })
        // 내 위치로 찾았으면, 가장 가까운 약국의 시/도·시/군/구를 검색 칸에 맞춰 둬요
        const region = near && data.items.length > 0 ? regionOf(data.items[0].addr) : null
        if (region) setForm(f => ({ ...f, ...region }))
      })
      .catch(err => setAnswer({ key, total: 0, items: [], error: err.message }))
  }, [ready, near, lat, lon, sido, sigungu, name, page, showAll, key, retry])

  // 주소에 '문 닫은 곳도 보기'를 남긴 채로 검색 조건을 바꿔요
  const go = params => setSearchParams(showAll ? { ...params, all: '1' } : params)

  // 체크를 바꾸면 지금 검색 조건은 그대로, all만 넣고 빼요 (1쪽부터)
  const toggleAll = checked => {
    const next = Object.fromEntries(searchParams)
    delete next.page
    if (checked) next.all = '1'
    else delete next.all
    setSearchParams(next)
  }

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
        go({ lat: pos.coords.latitude.toFixed(5), lon: pos.coords.longitude.toFixed(5) })
      },
      err => setGeo({ busy: false, error: GEO_ERROR[err.code] ?? GEO_ERROR[2] }),
      { timeout: 10000 },
    )
  }

  // 시/도를 바꾸면 시/군/구 목록도 바뀌어야 해요
  const changeSido = value => {
    setForm({ ...form, sido: value, sigungu: sigunguOf(value)[0] ?? '' })
  }

  const handleSearch = e => {
    e.preventDefault()
    go({ sido: form.sido, sigungu: form.sigungu, name: form.name.trim() })   // 새 검색은 1쪽부터
  }

  const goPage = p => {
    go({ sido, sigungu, name, page: String(p) })
    window.scrollTo(0, 0)
  }

  const showResult = ready && !loading && !answer.error

  // 문 닫은 약국 카드는 회색 바탕으로 (문 닫은 곳도 볼 때만 섞여 나와요)
  const cardStyle = p => {
    if (p.is_open)
      return { ...CARD, background: 'var(--surface)'}
    return { ...CARD, background: 'var(--surface-muted)'}
      
  }

  return (
    <div style={COLUMN}>
      {/* 시안 WEB-PHARMACY: 제목 + 기준 시각 줄, 오른쪽에 내 위치·시/도·시/군/구 */}
      <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', justifyContent: 'space-between', gap: 12 }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
          <h1 className="title">지금 문 연 약국</h1>
          <p className="muted" style={{ margin: 0 }}>
            {nowLabel()} 기준
            {showResult && name !== '' && ` · '${name}' ${answer.total}곳 · 문 연 곳 먼저`}
            {showResult && name === '' && ` · ${showAll ? '약국' : '영업 중'} ${answer.total}곳 · ${near ? '가까운 순' : '이름순'}`}
            {showResult && totalPages > 1 && ` · ${page} / ${totalPages}쪽`}
          </p>
        </div>

        <form style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }} onSubmit={handleSearch}>
          <button type="button" onClick={handleNear} disabled={geo.busy || loading} aria-pressed={near}
            className="btn" style={{ ...TOOL, border: '1px solid var(--primary)', background: 'var(--primary-bg)', color: 'var(--primary-text)', fontWeight: 700 }}>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" aria-hidden="true"><circle cx="12" cy="12" r="3" /><path d="M12 2v3M12 19v3M2 12h3M19 12h3" /></svg>
            {geo.busy ? '찾는 중' : '내 위치'}
          </button>
          <label htmlFor="sido" style={HIDDEN}>시/도</label>
          <select id="sido" className="input" style={TOOL}
            value={form.sido} onChange={e => changeSido(e.target.value)}>
            <option value="">전국 (이름으로 찾을 때)</option>
            {SIDO.map(s => <option key={s} value={s}>{s}</option>)}
          </select>
          {sigunguOf(form.sido).length > 0 && (<>
            <label htmlFor="sigungu" style={HIDDEN}>시/군/구</label>
            <select id="sigungu" className="input" style={TOOL}
              value={form.sigungu} onChange={e => setForm({ ...form, sigungu: e.target.value })}>
              {sigunguOf(form.sido).map(g => <option key={g} value={g}>{g}</option>)}
            </select>
          </>)}
          <label htmlFor="pharmacy-name" style={HIDDEN}>약국 이름 (선택)</label>
          <input id="pharmacy-name" type="search" className="input" style={{ ...TOOL, width: 170 }} placeholder="약국 이름 (선택)"
            value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} />
          <button type="submit" className="btn btn-primary" style={TOOL} disabled={loading}>찾기</button>
        </form>
      </div>

      {name === '' && (
        <label style={{ display: 'flex', alignItems: 'center', gap: 8, minHeight: 44, alignSelf: 'flex-start', fontSize: 15, cursor: 'pointer' }}>
          <input type="checkbox" checked={showAll} onChange={e => toggleAll(e.target.checked)} style={{ width: 20, height: 20 }} />
          문 닫은 곳도 보기
        </label>
      )}

      {geo.error && <p role="alert" style={{ margin: 0, color: 'var(--text)' }}>{geo.error}</p>}
      {!ready && <p className="muted" style={{ margin: 0 }}>내 위치를 누르거나, 지역을 고르거나, 약국 이름을 적어 주세요.</p>}
      {loading && <Loading text="문 연 약국을 찾는 중이에요" />}
      {ready && !loading && answer.error && <ErrorMessage message={answer.error} onRetry={() => setRetry(r => r + 1)} />}

      {showResult && answer.total === 0 && (
        <AlertBox type="info" title={showAll || name ? '약국을 찾지 못했어요' : '지금 문 연 약국을 찾지 못했어요'}>
          <p>{name
            ? `'${name}'(이)라는 약국이 없어요. 이름을 줄여서(예: "온누리") 다시 찾아 보세요.`
            : showAll
            ? '이 지역의 약국 정보가 없어요. 다른 지역으로 찾아 보세요.'
            : '지금 영업 중인 약국이 없어요. "문 닫은 곳도 보기"를 켜면 내일 갈 약국을 고를 수 있어요.'}</p>
        </AlertBox>
      )}

      {showResult && answer.items.length > 0 && (
        <section aria-label="약국 목록" style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          {answer.items.map((p, i) => (
            <article key={p.id} className="card" style={cardStyle(p)}>
              <span style={{ ...NUMBER, background: p.is_open ? 'var(--text)' : 'var(--text-muted)' }}>{(page - 1) * PAGE_SIZE + i + 1}</span>
              <div style={{ flex: 1, minWidth: 0, display: 'flex', flexDirection: 'column', gap: 3 }}>
                <strong style={{ fontSize: 17, overflowWrap: 'anywhere' }}>{p.name}</strong>
                <span style={{ fontSize: 15, color: 'var(--text-muted)' }}>{infoLine(p)}</span>
                <span className="muted" style={{ overflowWrap: 'anywhere' }}>{p.addr}</span>
              </div>
              {p.lat && p.lon && (
                <a href={mapLink(p)} target="_blank" rel="noreferrer" aria-label={`${p.name} 지도에서 보기`} style={ICON_BTN}>
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinejoin="round" aria-hidden="true"><path d="M12 21s-7-6.2-7-11a7 7 0 0 1 14 0c0 4.8-7 11-7 11z" /><circle cx="12" cy="10" r="2.5" /></svg>
                </a>
              )}
              {p.tel && (
                <a href={`tel:${p.tel}`} aria-label={`${p.name}에 전화 ${p.tel}`} style={ICON_BTN}>
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinejoin="round" aria-hidden="true"><path d="M5 4h4l2 5-2.5 1.5a11 11 0 0 0 5 5L15 13l5 2v4a2 2 0 0 1-2 2A16 16 0 0 1 3 6a2 2 0 0 1 2-2z" /></svg>
                </a>
              )}
            </article>
          ))}
          <p className="muted" style={{ margin: '4px 0 0', lineHeight: 1.55 }}>
            영업시간은 국립중앙의료원 공공데이터 기준이라 실제와 다를 수 있어요. 방문 전 전화로 확인하세요.
          </p>
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
