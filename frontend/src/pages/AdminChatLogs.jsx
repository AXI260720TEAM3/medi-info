import { Fragment, useEffect, useState } from 'react'
import Badge from '../components/Badge'
import { CheckDetail } from './AdminAnswerChecks'
import { shortReason } from './adminCheckReasons'

// 관리자 질문 기록 표 (H-1). 칩 이름은 서버(routes/admin.py FILTERS)와 같아요
// 건수가 0인 칩은 숨겨요 (전체는 늘 보여요)
const CHIPS = [
  { id: 'all', label: '전체' },
  { id: 'blocked', label: '차단·안내' },
  { id: 'ask_drug', label: '약 되물음' },
  { id: 'check_failed', label: 'AI 검증 걸림' },
  { id: 'reported', label: '도움 안 됨·신고' },
  { id: 'interaction', label: '함께 먹기' },
  { id: 'unclassified', label: '분류 못 함' },
]
const PAGE = 20
// 입력칸 기본 모양 (index.css에 입력 요소 공용 스타일이 아직 없어서 여기서 맞춰요. 디자인 개선 때 공용으로 옮길 것)
const FIELD_STYLE = { flex: '1 1 260px', minWidth: 0, minHeight: 44, padding: '0 12px', border: '1.5px solid var(--border-strong)', borderRadius: 'var(--radius)', font: 'inherit', fontSize: 15, background: 'var(--surface)', boxSizing: 'border-box' }

// 이 답을 무엇이 만들었나: 차단 규칙 → 약 되물음 → 함께 먹기(DUR) → AI(검증 결과) 순서로 정해요
function result(log) {
  if (log.blocked) {
    return log.block_reason === 'redirect' ? ['taboo', '안내 · 추천·진단 거절'] : ['taboo', '차단 · 119 안내']
  }
  if (log.question_type === '약확인') return ['none', '약 되물음']
  if (log.question_type === '함께먹기') return ['none', '함께 먹기 판정']
  if (log.check_result === 'pass') return ['notice', 'AI · 통과']
  if (log.check_result === 'retry_pass') return ['notice', 'AI · 다시 써서 통과']
  if (log.check_result === 'fallback') return ['none', 'AI · 안내로 대체']
  if (log.question_type === '약정보') return ['none', '약 정보 답']
  return ['none', '분류 못 함']
}

// 오늘 15:02 / 어제 19:12 / 11. 9. 10:30 (한국 시간)
function when(iso) {
  const d = new Date(iso)
  const time = d.toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit', hour12: false })
  const day = (x) => x.toLocaleDateString('ko-KR')
  const today = new Date()
  const yesterday = new Date(Date.now() - 864e5)
  if (day(d) === day(today)) return `오늘 ${time}`
  if (day(d) === day(yesterday)) return `어제 ${time}`
  return `${d.getMonth() + 1}. ${d.getDate()}. ${time}`
}
const sec = (ms) => (ms != null ? `${(ms / 1000).toFixed(1)}초` : '-')

function LogRow({ log }) {
  const [open, setOpen] = useState(false)
  const [showCheck, setShowCheck] = useState(false)
  const [type, label] = result(log)
  return (
    <Fragment>
      <tr style={{ borderTop: '1px solid var(--border)', background: open ? 'var(--primary-bg)' : undefined }}>
        <td className="muted" style={{ whiteSpace: 'nowrap' }}>{when(log.created_at)}</td>
        <td style={{ fontWeight: 500 }}>{log.question}</td>
        <td>{log.item_name ?? '—'}</td>
        <td>
          <span style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
            <span style={{ whiteSpace: 'nowrap' }}><Badge type={type}>{label}</Badge></span>
            {(log.reported || log.feedback === -1) && <Badge type="caution">{log.reported ? '신고' : '도움 안 됨'}</Badge>}
            {log.is_test && <Badge type="none">시험</Badge>}
          </span>
        </td>
        <td className="muted" style={{ textAlign: 'right', whiteSpace: 'nowrap' }}>{sec(log.response_ms)}</td>
        <td className="med-table-action">
          <button type="button" className="btn btn-secondary" aria-expanded={open} onClick={() => setOpen(!open)}
            aria-label={open ? '답 접기' : '답 펼치기'}>{open ? '접기' : '답 보기'}</button>
        </td>
      </tr>
      {open && (
        <tr style={{ background: 'var(--primary-bg)' }}>
          <td></td>
          <td colSpan={5} style={{ paddingBottom: 16 }}>
            <p className="muted" style={{ margin: '0 0 6px' }}>사용자에게 간 답</p>
            <div style={{ padding: '12px 14px', background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 'var(--radius)', lineHeight: 1.7, whiteSpace: 'pre-wrap' }}>
              {log.answer || '없음'}
            </div>
            {log.check_reason && (
              <p style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap', margin: '10px 0 0' }}>
                <span>AI 검증: 첫 답이 <strong>{shortReason(log.check_reason)}</strong>(으)로 걸려
                  {log.check_result === 'retry_pass' ? ' 다시 써서 통과' : ' 정해진 안내로 대체'}
                  {log.retry_ms != null && ` (+${sec(log.retry_ms)})`}</span>
                <button type="button" className="btn btn-secondary" aria-expanded={showCheck} onClick={() => setShowCheck(!showCheck)}>
                  {showCheck ? '검증 과정 닫기' : '검증 과정 보기'}
                </button>
              </p>
            )}
            {showCheck && <CheckDetail logId={log.log_id} />}
          </td>
        </tr>
      )}
    </Fragment>
  )
}

function AdminChatLogs() {
  const [only, setOnly] = useState('all')
  const [days, setDays] = useState(7)
  const [hideTest, setHideTest] = useState(true)
  const [draft, setDraft] = useState('')   // 검색칸에 치는 중인 글자
  const [q, setQ] = useState('')           // [찾기]를 누른 검색어
  const [offset, setOffset] = useState(0)
  const [data, setData] = useState(null)
  const [error, setError] = useState('')

  // 조건이 바뀌면 첫 쪽부터
  const change = (fn) => (value) => { fn(value); setOffset(0) }

  useEffect(() => {
    const params = new URLSearchParams({ only, days, hide_test: hideTest, q, limit: PAGE, offset })
    fetch(`/api/admin/chat-logs?${params}`)
      .then(async (res) => {
        const body = await res.json().catch(() => ({}))
        if (!res.ok) throw new Error(typeof body.detail === 'string' ? body.detail : '기록을 불러오지 못했어요.')
        return body
      })
      .then((d) => { setData(d); setError('') })
      .catch((err) => setError(err.message))
  }, [only, days, hideTest, q, offset])

  return (
    <section className="card">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', gap: 12, flexWrap: 'wrap' }}>
        <h2 style={{ margin: 0 }}>질문 기록</h2>
        <span className="muted">질문은 개인정보 모양을 가려 저장하고, 90일이 지나면 지워요</span>
      </div>

      <form role="search" style={{ display: 'flex', gap: 12, flexWrap: 'wrap', alignItems: 'center', margin: '16px 0 12px' }}
        onSubmit={(e) => { e.preventDefault(); change(setQ)(draft.trim()) }}>
        <label htmlFor="log-search" className="sr-only" style={{ position: 'absolute', width: 1, height: 1, overflow: 'hidden', clipPath: 'inset(50%)' }}>질문이나 약 이름으로 찾기</label>
        <input id="log-search" type="search" value={draft} onChange={(e) => setDraft(e.target.value)} maxLength={100}
          placeholder="질문이나 약 이름으로 찾기" style={FIELD_STYLE} />
        <button type="submit" className="btn btn-secondary">찾기</button>
        <label style={{ display: 'inline-flex', alignItems: 'center', gap: 8 }}>
          기간
          <select value={days} onChange={(e) => change(setDays)(Number(e.target.value))} style={{ ...FIELD_STYLE, flex: 'none' }}>
            <option value={7}>최근 7일</option>
            <option value={30}>최근 30일</option>
            <option value={90}>전체(90일)</option>
          </select>
        </label>
        <label style={{ display: 'inline-flex', alignItems: 'center', gap: 8, minHeight: 44, fontWeight: 700 }}>
          <input type="checkbox" checked={hideTest} onChange={(e) => change(setHideTest)(e.target.checked)} style={{ width: 18, height: 18 }} />
          시험·평가 질문 빼기
        </label>
      </form>

      {data && (
        <div role="group" aria-label="결과로 거르기" style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 12 }}>
          {CHIPS.filter(c => c.id === 'all' || data.counts[c.id] > 0 || c.id === only).map(c => (
            <button key={c.id} type="button" aria-pressed={only === c.id} onClick={() => change(setOnly)(c.id)}
              className={only === c.id ? 'btn btn-primary' : 'btn btn-secondary'} style={{ borderRadius: 999 }}>
              {c.label} <span style={{ fontWeight: 500 }}>{data.counts[c.id]}</span>
            </button>
          ))}
        </div>
      )}

      {error && <p style={{ color: 'var(--danger-text)' }}>{error}</p>}
      {!data && !error && <p>기록을 불러오는 중...</p>}
      {data && (<>
        <p className="muted">
          <strong style={{ color: 'var(--text)' }}>{data.total}건</strong>
          {hideTest && data.hidden_test > 0 && ` · 시험·평가 질문 ${data.hidden_test}건은 숨겼어요`}
          {q && ` · '${q}' 검색`}
        </p>
        {data.items.length === 0 ? <p>조건에 맞는 질문이 없어요.</p> : (
          <div className="table-card">
            <table className="med-table" style={{ minWidth: 860 }}>
              <thead>
                <tr><th style={{ width: 110 }}>시각</th><th>질문</th><th style={{ width: 170 }}>약</th><th style={{ width: 210 }}>결과</th><th style={{ width: 70, textAlign: 'right' }}>응답</th><th style={{ width: 90 }}></th></tr>
              </thead>
              <tbody>
                {data.items.map(log => <LogRow key={log.log_id} log={log} />)}
              </tbody>
            </table>
          </div>
        )}
        <nav aria-label="쪽" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 12, flexWrap: 'wrap', marginTop: 12 }}>
          <span className="muted">{data.total ? `${offset + 1}–${Math.min(offset + PAGE, data.total)} / ${data.total}건` : ''}</span>
          <span style={{ display: 'flex', gap: 8 }}>
            <button type="button" className="btn btn-secondary" disabled={offset === 0} onClick={() => setOffset(offset - PAGE)}>이전</button>
            <button type="button" className="btn btn-secondary" disabled={offset + PAGE >= data.total} onClick={() => setOffset(offset + PAGE)}>다음</button>
          </span>
        </nav>
      </>)}
    </section>
  )
}

export default AdminChatLogs
