import { Fragment, useEffect, useState } from 'react'
import Badge from '../components/Badge'
import { CheckDetail } from './AdminAnswerChecks'
import { shortReason } from './adminCheckReasons'
import { FIELD_STYLE } from './adminStyles'

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

// 동의어 사전 (data/dict/synonym.csv). 사전은 배포 때마다 CSV에서 통째로 다시 넣어서(dict-load),
// 여기서 DB에 바로 넣으면 다음 배포 때 사라져요. 그래서 CSV에 붙일 한 줄을 만들어 주고, PR로 넣어요
const SYN_TYPES = {
  오타_제품명: { label: '오타 → 제품명', hint: '예: 타이래놀 → 타이레놀. 약 이름을 잘못 쳐서 되물은 질문에' },
  일상_공식: { label: '일상어 → 공식 증상', hint: '예: 지끈 → 두통. 증상을 못 알아들은 질문에' },
}
let synonymCache = null   // 사전은 자주 안 바뀌어서 화면을 새로 열 때까지 한 번만 불러요
const loadSynonyms = () => (synonymCache ??= fetch('/api/admin/dict').then(r => r.json()).then(d => d.synonym ?? []).catch(() => { synonymCache = null; return [] }))
const CSV_UNSAFE = /[,"\n\r]/   // CSV 칸을 깨는 글자 (쉼표·따옴표·줄바꿈)

function DictCandidate({ log }) {
  const [open, setOpen] = useState(false)
  const [type, setType] = useState(log.question_type === '약확인' ? '오타_제품명' : '일상_공식')
  const [word, setWord] = useState((log.question.split(/\s+/)[0] || '').slice(0, 30))
  const [standard, setStandard] = useState('')
  const [synonyms, setSynonyms] = useState([])
  const [copied, setCopied] = useState(false)

  useEffect(() => { if (open) loadSynonyms().then(setSynonyms) }, [open])

  if (!open) {
    return <p style={{ margin: '10px 0 0' }}><button type="button" className="btn btn-secondary" onClick={() => setOpen(true)}>사전 후보 만들기</button></p>
  }
  const w = word.trim(), s = standard.trim()
  const problem = !w || !s ? '두 칸을 모두 채워 주세요.'
    : CSV_UNSAFE.test(w + s) ? '쉼표·따옴표·줄바꿈은 쓸 수 없어요.'
    : w === s ? '바꿀 말과 표준 말이 같아요.' : ''
  const existing = synonyms.find(x => x.word === w)
  const line = `${w},${s},${type}`
  const copy = () => navigator.clipboard?.writeText(line).then(() => setCopied(true)).catch(() => setCopied(false))
  const field = { minHeight: 44, padding: '0 10px', border: '1.5px solid var(--border-strong)', borderRadius: 'var(--radius)', font: 'inherit', fontSize: 15, boxSizing: 'border-box' }

  return (
    <div style={{ marginTop: 12, padding: 14, border: '1px solid var(--border)', borderRadius: 'var(--radius)', background: 'var(--surface)' }}>
      <strong>사전 후보 만들기</strong>
      <p className="muted" style={{ margin: '4px 0 10px' }}>{SYN_TYPES[type].hint}</p>
      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center' }}>
        <label style={{ display: 'inline-flex', gap: 6, alignItems: 'center' }}>종류
          <select value={type} onChange={(e) => setType(e.target.value)} style={field}>
            {Object.entries(SYN_TYPES).map(([k, v]) => <option key={k} value={k}>{v.label}</option>)}
          </select>
        </label>
        <label style={{ display: 'inline-flex', gap: 6, alignItems: 'center' }}>바꿀 말
          <input value={word} maxLength={30} onChange={(e) => { setWord(e.target.value); setCopied(false) }} style={{ ...field, width: 150 }} />
        </label>
        <span aria-hidden="true">→</span>
        <label style={{ display: 'inline-flex', gap: 6, alignItems: 'center' }}>{type === '오타_제품명' ? '제품명' : '공식 증상'}
          <input value={standard} maxLength={30} onChange={(e) => { setStandard(e.target.value); setCopied(false) }} style={{ ...field, width: 150 }} />
        </label>
      </div>
      {existing && <p style={{ margin: '10px 0 0' }}><Badge type="caution">이미 있음</Badge> 사전에 <strong>{existing.word} → {existing.standard}</strong>({existing.syn_type})가 있어요.</p>}
      {problem ? <p className="muted" style={{ margin: '10px 0 0' }}>{problem}</p> : (
        <div style={{ marginTop: 10, display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
          <code style={{ padding: '8px 10px', background: 'var(--surface-muted)', borderRadius: 8 }}>{line}</code>
          <button type="button" className="btn btn-secondary" onClick={copy}>{copied ? '복사했어요' : '한 줄 복사'}</button>
        </div>
      )}
      <p className="muted" style={{ margin: '10px 0 0' }}>
        <code>data/dict/synonym.csv</code> 맨 아래에 붙여 PR을 올리고, 머지 뒤 배포하면 사전에 들어가요. (화면에서 DB에 바로 넣으면 다음 배포 때 CSV로 덮여 사라져요)
      </p>
    </div>
  )
}

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
            {!log.blocked && (log.question_type === '약확인' || !log.question_type) && <DictCandidate log={log} />}
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
