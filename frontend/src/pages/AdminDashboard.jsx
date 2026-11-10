import { useEffect, useState } from 'react'
import Badge from '../components/Badge'

// 관리자 대시보드 (H-4): 최근 며칠의 질문 현황과 서버 상태
const RANGES = [7, 30]
const DICT_LABELS = { symptom_keyword: '위험 증상', caution_keyword: '주의 대상', synonym: '동의어', notice_text: '고정 문구' }

function Stat({ label, value, note }) {
  return (
    <div className="admin-stat">
      <span className="muted">{label}</span>
      <strong>{value}</strong>
      {note && <span className="muted">{note}</span>}
    </div>
  )
}

// 날짜별 질문 수 막대 (한 가지 값이라 범례 없이 제목이 이름 역할). 막대에 마우스를 올리면 숫자가 보여요
function DailyBars({ daily }) {
  const max = Math.max(1, ...daily.map(d => d.total))
  return (
    <div className="admin-bars" role="img" aria-label="날짜별 질문 수">
      {daily.map(d => (
        <div key={d.day} className="admin-bar-col" title={`${d.day}: 질문 ${d.total}건 (차단 ${d.blocked}건)`}>
          <span className="admin-bar-value">{d.total > 0 ? d.total : ''}</span>
          <div className="admin-bar" style={{ height: `${(d.total / max) * 100}%` }} />
          <span className="admin-bar-label">{d.day.slice(5).replace('-', '/')}</span>
        </div>
      ))}
    </div>
  )
}

function AdminDashboard() {
  const [days, setDays] = useState(7)
  const [data, setData] = useState(null)
  const [error, setError] = useState('')

  const changeDays = (value) => {
    setDays(value)
    setData(null)
    setError('')
  }

  useEffect(() => {
    fetch(`/api/admin/dashboard?days=${days}`)
      .then(async (res) => {
        const body = await res.json().catch(() => ({}))
        if (!res.ok) throw new Error(typeof body.detail === 'string' ? body.detail : '대시보드를 불러오지 못했어요.')
        return body
      })
      .then(setData)
      .catch((err) => setError(err.message))
  }, [days])

  if (error) return <p style={{ color: 'var(--danger-text)' }}>{error}</p>

  return (<>
    <div className="admin-tabs">
      {RANGES.map(r => (
        <button key={r} type="button" className={days === r ? 'btn btn-primary' : 'btn btn-secondary'}
          onClick={() => changeDays(r)}>최근 {r}일</button>
      ))}
    </div>
    {!data ? <p>불러오는 중...</p> : (<>
      <section className="card">
        <h2>서버 상태</h2>
        <p>
          DB <Badge type="notice">정상</Badge>{' '}
          AI 모델 서버 {data.status.ollama.ok
            ? <Badge type="notice">정상 · {data.status.ollama.ms}ms</Badge>
            : <Badge type="taboo">응답 없음</Badge>}
        </p>
        {!data.status.ollama.ok && <p className="muted">AI 질문이 503으로 실패해요. WSL에서 Ollama가 켜져 있는지 확인해 주세요.</p>}
      </section>

      <section className="card">
        <h2>질문 현황 (최근 {data.days}일)</h2>
        <div className="admin-stats">
          <Stat label="질문" value={`${data.totals.questions}건`} />
          <Stat label="차단·안내" value={`${data.totals.blocked}건`} />
          <Stat label="분류 못 함" value={`${data.totals.unclassified}건`} note="사전 보강 후보" />
          <Stat label="신고·도움 안 됨" value={`${data.totals.reported}건`} />
          <Stat label="평균 응답" value={data.response.avg_ms != null ? `${(data.response.avg_ms / 1000).toFixed(1)}초` : '-'}
            note={data.response.p95_ms != null ? `느린 5%는 ${(data.response.p95_ms / 1000).toFixed(1)}초 넘게 (차단 제외 ${data.response.measured}건)` : '아직 잰 기록이 없어요'} />
        </div>
        <h3>날짜별 질문 수</h3>
        <DailyBars daily={data.daily} />
      </section>

      <section className="card">
        <h2>질문 종류</h2>
        <div className="table-card">
          <table className="med-table">
            <thead><tr><th>종류</th><th>건수</th></tr></thead>
            <tbody>
              {data.types.map(t => <tr key={t.type}><td>{t.type}</td><td>{t.count}</td></tr>)}
            </tbody>
          </table>
        </div>
        {data.types.length === 0 && <p>이 기간에는 질문이 없어요.</p>}
        <p className="muted">
          사전 줄 수: {Object.entries(data.dict_counts).map(([k, v]) => `${DICT_LABELS[k] ?? k} ${v}`).join(' · ')}
        </p>
      </section>
    </>)}
  </>)
}
export default AdminDashboard
