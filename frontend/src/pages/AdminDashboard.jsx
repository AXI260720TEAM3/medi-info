import { useEffect, useState } from 'react'
import Badge from '../components/Badge'
import AdminAnswerChecks from './AdminAnswerChecks'

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

// 서버 상태: 통계와 따로 불러요 (/api/admin/health). 하나가 실패해도 나머지는 보여요
// 색은 배지 규칙대로: 정상은 파랑(notice), 느리거나 설정이 어긋남은 주의(caution), 기능이 실패하면 금기색(taboo)
const STATE = { ok: ['notice', '정상'], warn: ['caution', '확인 필요'], down: ['taboo', '응답 없음'] }

function HealthRow({ label, item, children }) {
  const [type, word] = STATE[item.state] ?? STATE.down
  return (
    <tr>
      <td>{label}</td>
      <td><Badge type={type}>{item.state === 'down' && label === '사전' ? '비어 있음' : word}{item.ms != null ? ` · ${item.ms}ms` : ''}</Badge></td>
      <td>{children}{item.detail && <div className="muted">{item.detail}</div>}</td>
    </tr>
  )
}

function HealthCard() {
  const [health, setHealth] = useState(null)
  const [error, setError] = useState('')
  const [checked, setChecked] = useState(null)

  const load = () => {
    fetch('/api/admin/health')
      .then(async (res) => {
        if (!res.ok) throw new Error(res.status >= 500
          ? '서버 상태를 확인하지 못했어요. 관리자 확인에도 DB를 쓰기 때문에, DB가 멈췄을 가능성이 커요.'
          : '서버 상태를 불러오지 못했어요.')
        return res.json()
      })
      .then((d) => { setHealth(d); setError(''); setChecked(new Date()) })
      .catch((err) => setError(err.message))
  }
  useEffect(load, [])

  return (
    <section className="card">
      <h2>서버 상태</h2>
      {error && <p><Badge type="taboo">확인 실패</Badge> {error}</p>}
      {!health && !error && <p>확인하는 중...</p>}
      {health && (
        <div className="table-card">
          <table className="med-table">
            <thead><tr><th>대상</th><th>상태</th><th>내용</th></tr></thead>
            <tbody>
              <HealthRow label="DB" item={health.db}>PostgreSQL (k8s db-0)</HealthRow>
              <HealthRow label="AI 모델 서버" item={health.ollama}>
                {health.ollama.model && (health.ollama.loaded
                  ? `${health.ollama.model} · 올라가 있음 (${health.ollama.size_gb}GB, GPU ${health.ollama.gpu_pct}%, 문맥 ${health.ollama.ctx})`
                  : `${health.ollama.model} · 쉬는 중 (다음 질문이 모델을 올리느라 10초쯤 더 걸려요)`)}
              </HealthRow>
              <HealthRow label="사전" item={health.dict}>
                {health.dict.counts && Object.entries(health.dict.counts).map(([k, v]) => `${DICT_LABELS[k] ?? k} ${v}`).join(' · ')}
              </HealthRow>
            </tbody>
          </table>
        </div>
      )}
      <p className="muted">
        {checked && `${checked.toLocaleTimeString('ko-KR')}에 확인 · `}
        <button type="button" className="btn btn-secondary" onClick={load}>다시 확인</button>
      </p>
    </section>
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

  return (<>
    <HealthCard />
    <div className="admin-tabs">
      {RANGES.map(r => (
        <button key={r} type="button" className={days === r ? 'btn btn-primary' : 'btn btn-secondary'}
          onClick={() => changeDays(r)}>최근 {r}일</button>
      ))}
    </div>
    {error ? <p style={{ color: 'var(--danger-text)' }}>{error}</p> : !data ? <p>불러오는 중...</p> : (<>

      <section className="card">
        <h2>질문 현황 (최근 {data.days}일)</h2>
        <div className="admin-stats">
          <Stat label="질문" value={`${data.totals.questions}건`} />
          <Stat label="차단·안내" value={`${data.totals.blocked}건`} />
          <Stat label="약 되물음" value={`${data.totals.ask_drug}건`} note="약 이름만 적었거나 같은 이름이 여러 개" />
          <Stat label="분류 못 함" value={`${data.totals.unclassified}건`} note="그 밖에 종류를 못 정한 답" />
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
      </section>
    </>)}
    <AdminAnswerChecks days={days} />
  </>)
}
export default AdminDashboard
