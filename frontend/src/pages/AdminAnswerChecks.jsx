import { useEffect, useState } from 'react'
import Badge from '../components/Badge'

// 관리자 대시보드 "AI 답변 검증": AI가 쓴 답을 내보내기 전에 코드가 검사한 결과 (backend chat_answer.py)
// 첫 답 통과 → 그대로 / 걸리면 한 번 다시 쓰게 함 → 또 걸리면 정해진 안내로 대체
// 색: 통과는 파랑, 다시 써서 통과는 옅은 파랑, 대체는 회색(안전장치가 일한 것이지 고장이 아니라서). 막힌 사유 배지만 주의색

// chat_answer.py의 사유 문장 → [짧은 이름, 쉬운 설명]. 모르는 사유는 원문 그대로 보여 줘요
const REASONS = {
  '공식 자료에 없는 숫자': ['자료에 없는 숫자', 'AI가 근거 자료에 없는 숫자를 썼어요'],
  '공식 자료에 없는 용량·횟수 숫자': ['자료에 없는 용량·횟수', '용량을 물었는데 자료에 없는 정·회 숫자를 썼어요'],
  '질문과 무관하거나 개인별 검증이 필요한 숫자·용량 표현': ['묻지 않은 숫자·용량', '묻지 않은 용량을 덧붙였거나, 개인 질문에 숫자를 썼어요'],
  '복용 안전성을 단정하는 표현': ['복용 안전성 단정', '“드셔도 괜찮아요”처럼 단정했어요'],
  '약 추천·진단·안전 단정 등 금지 표현': ['금지 표현', '약 추천·진단 같은 말을 썼어요'],
  '공식 자료에 명시된 연령별 복용 금지 안내 누락': ['연령별 복용 금지 누락', '자료의 나이 제한을 빠뜨렸어요'],
  '한자가 포함된 표현': ['한자 섞임', '服用처럼 한자가 들어갔어요'],
}
const shortReason = (r) => REASONS[r]?.[0] ?? r
const RESULTS = {
  pass: { label: '첫 답 통과', color: 'var(--primary)' },
  retry_pass: { label: '다시 써서 통과', color: '#93C5FD' },
  fallback: { label: '정해진 안내로 대체', color: '#6B7280' },
}
const fmt = (iso) => new Date(iso).toLocaleString('ko-KR', { month: 'numeric', day: 'numeric', hour: '2-digit', minute: '2-digit' })
const pct = (a, b) => (b ? `${Math.round((a / b) * 100)}%` : '-')
const sec = (ms) => (ms != null ? `${(ms / 1000).toFixed(1)}초` : '-')

async function getJson(url) {
  const res = await fetch(url)
  const body = await res.json().catch(() => ({}))
  if (!res.ok) throw new Error(typeof body.detail === 'string' ? body.detail : '불러오지 못했어요.')
  return body
}

function ResultBadge({ result }) {
  if (result === 'retry_pass') return <Badge type="notice">다시 써서 통과</Badge>
  if (result === 'fallback') return <Badge type="none">정해진 안내로 대체</Badge>
  return <Badge type="notice">첫 답 통과</Badge>
}

// 질문 하나의 검증 과정: 질문 → 막힌 첫 초안 → 다시 쓰기 → 결과
function CheckDetail({ logId }) {
  const [row, setRow] = useState(null)
  const [error, setError] = useState('')
  useEffect(() => {
    getJson(`/api/admin/answer-checks/${logId}`).then(setRow).catch((err) => setError(err.message))
  }, [logId])

  if (error) return <p style={{ color: 'var(--danger-text)' }}>{error}</p>
  if (!row) return <p>불러오는 중...</p>
  const firstMs = row.response_ms != null && row.retry_ms != null ? row.response_ms - row.retry_ms : null
  const step = { display: 'flex', flexDirection: 'column', gap: 6, padding: '12px 0', borderTop: '1px solid var(--border)' }
  const quote = { margin: 0, padding: '12px 14px', borderRadius: 10, lineHeight: 1.7, whiteSpace: 'pre-wrap' }

  return (
    <div className="card" style={{ marginTop: 12 }}>
      <p className="muted" style={{ margin: 0 }}>{fmt(row.created_at)} · {row.question_type ?? '분류 못 함'} · 전체 {sec(row.response_ms)}</p>

      <div style={step}>
        <strong>1. AI 첫 초안 <Badge type="caution">걸림 · {shortReason(row.check_reason)}</Badge></strong>
        <span className="muted">{REASONS[row.check_reason]?.[1] ?? row.check_reason} · 사용자에게 보내지 않음{firstMs != null ? ` · ${sec(firstMs)}` : ''}</span>
        <blockquote style={{ ...quote, background: 'var(--surface-muted)' }}>{row.rejected_draft ?? '(초안을 저장하기 전의 기록이에요)'}</blockquote>
      </div>

      <div style={step}>
        <strong>2. 다시 쓰기 (한 번만) · {sec(row.retry_ms)}</strong>
        {row.check_result === 'retry_pass'
          ? <span>다시 쓴 답이 검사를 통과했어요.</span>
          : <span><Badge type="caution">또 걸림 · {shortReason(row.retry_reason)}</Badge> 그래서 AI 글 대신 정해진 안내를 보냈어요.</span>}
      </div>

      <div style={step}>
        <strong>3. 사용자에게 간 답 <ResultBadge result={row.check_result} /></strong>
        <blockquote style={{ ...quote, background: 'var(--primary-bg)' }}>{row.answer}</blockquote>
      </div>
    </div>
  )
}

function AdminAnswerChecks({ days }) {
  const [data, setData] = useState(null)
  const [error, setError] = useState('')
  const [open, setOpen] = useState(null)   // 자세히 본 질문 기록 번호

  useEffect(() => {
    setData(null)
    setError('')
    setOpen(null)
    getJson(`/api/admin/answer-checks?days=${days}`).then(setData).catch((err) => setError(err.message))
  }, [days])

  return (
    <section className="card">
      <h2>AI 답변 검증 <span className="muted" style={{ fontWeight: 500 }}>최근 {days}일</span></h2>
      <p className="muted">
        규칙이 정한 내용을 AI가 문장으로 쓰고, 내보내기 전에 코드가 다시 검사해요.
        걸리면 한 번 다시 쓰게 하고, 또 걸리면 AI 글 대신 정해진 안내를 보여 줘요.
      </p>
      {error && <p style={{ color: 'var(--danger-text)' }}>{error}</p>}
      {!data && !error && <p>불러오는 중...</p>}
      {data && (() => {
        const s = data.summary
        const failed = s.retry_pass + s.fallback
        if (s.ai === 0) {
          return <p>이 기간에는 AI가 쓴 답이 없어요. (검증 기록은 11/11 배포부터 쌓여요. AI를 안 부른 질문 {s.no_ai}건)</p>
        }
        return (<>
          <p style={{ fontSize: '1.1rem' }}>
            AI가 쓴 답 <strong>{s.ai}건</strong> 중 <strong>{s.pass + s.retry_pass}건</strong>이 검사를 통과해 사용자에게 갔고,
            {' '}<strong>{s.fallback}건</strong>은 정해진 안내로 바꿨어요.
          </p>
          <div role="img" aria-label={`첫 답 통과 ${s.pass}건, 다시 써서 통과 ${s.retry_pass}건, 정해진 안내로 대체 ${s.fallback}건`}
            style={{ display: 'flex', height: 24, borderRadius: 8, overflow: 'hidden', gap: 2 }}>
            {['pass', 'retry_pass', 'fallback'].map(k => s[k] > 0 && <div key={k} style={{ flex: s[k], background: RESULTS[k].color }} />)}
          </div>
          <p style={{ display: 'flex', gap: 20, flexWrap: 'wrap' }}>
            {['pass', 'retry_pass', 'fallback'].map(k => (
              <span key={k} style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}>
                <span style={{ width: 12, height: 12, borderRadius: 3, background: RESULTS[k].color }} />
                {RESULTS[k].label} <strong>{s[k]}</strong>
              </span>
            ))}
          </p>

          <div className="admin-stats">
            <div className="admin-stat"><span className="muted">첫 답 통과</span><strong>{pct(s.pass, s.ai)}</strong><span className="muted">{s.ai}건 중 {s.pass}건</span></div>
            <div className="admin-stat"><span className="muted">다시 써서 살린 비율</span><strong>{pct(s.retry_pass, failed)}</strong><span className="muted">걸린 {failed}건 중 {s.retry_pass}건</span></div>
            <div className="admin-stat"><span className="muted">정해진 안내로 대체</span><strong>{s.fallback}건</strong><span className="muted">AI 글을 내보내지 않음</span></div>
            <div className="admin-stat"><span className="muted">다시 쓰느라 더 걸린 시간</span><strong>{s.retry_ms_avg != null ? `+${sec(s.retry_ms_avg)}` : '-'}</strong><span className="muted">걸린 답의 평균</span></div>
          </div>

          {failed > 0 && (<>
            <h3>어디서 걸렸나 <span className="muted" style={{ fontWeight: 500 }}>첫 답 기준 {failed}건</span></h3>
            <div className="table-card">
              <table className="med-table">
                <thead><tr><th>사유</th><th>걸림</th><th>다시 써서 통과</th><th>대체</th></tr></thead>
                <tbody>
                  {data.reasons.map(r => (
                    <tr key={r.reason}>
                      <td><strong>{shortReason(r.reason)}</strong><div className="muted">{REASONS[r.reason]?.[1] ?? ''}</div></td>
                      <td style={{ minWidth: 140 }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                          <span style={{ flex: 1, height: 8, borderRadius: 999, background: 'var(--surface-muted)', overflow: 'hidden', display: 'flex' }}>
                            <span style={{ width: `${(r.n / data.reasons[0].n) * 100}%`, background: 'var(--primary)' }} />
                          </span>
                          <strong>{r.n}</strong>
                        </div>
                      </td>
                      <td>{r.saved}</td>
                      <td>{r.replaced}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <h3>최근에 막힌 초안</h3>
            <ul style={{ listStyle: 'none', padding: 0, margin: 0, display: 'flex', flexDirection: 'column', gap: 8 }}>
              {data.recent.map(c => (
                <li key={c.log_id} style={{ border: '1px solid var(--border)', borderRadius: 'var(--radius)', padding: '10px 14px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12 }}>
                    <strong>“{c.question}”</strong>
                    <span className="muted" style={{ whiteSpace: 'nowrap' }}>{fmt(c.created_at)}</span>
                  </div>
                  <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap', marginTop: 6 }}>
                    <Badge type="caution">{shortReason(c.check_reason)}</Badge>
                    <ResultBadge result={c.check_result} />
                    <button type="button" className="btn btn-secondary" style={{ marginLeft: 'auto' }}
                      aria-expanded={open === c.log_id} onClick={() => setOpen(open === c.log_id ? null : c.log_id)}>
                      {open === c.log_id ? '접기' : '자세히'}
                    </button>
                  </div>
                  {open === c.log_id && <CheckDetail logId={c.log_id} />}
                </li>
              ))}
            </ul>
          </>)}

          <p className="muted">
            규칙이 먼저 처리해 AI를 부르지 않은 질문 <strong>{s.no_ai}건</strong>(위험 신호 차단, 함께 먹기 판정, 자료 없음 안내 등)은 위 숫자에 넣지 않아요.
            검증 기록은 11/11 배포부터 쌓여서, 그 전 질문은 기록이 없어 이 숫자에 함께 세어져요.
          </p>
        </>)
      })()}
    </section>
  )
}
export default AdminAnswerChecks
