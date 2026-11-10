import { useEffect, useState } from 'react'
import Badge from '../components/Badge'

// 관리자 사전 탭 (H-2): 문장 시험기 + 지금 DB에 있는 사전 보기
// 사전을 고치는 곳은 여기가 아니라 data/dict/*.csv (PR로 고치고, 배포 때 dict Job이 DB에 넣어요)
const DICTS = [
  { id: 'symptom_keyword', label: '위험 증상', cols: ['keyword', 'category', 'action'] },
  { id: 'caution_keyword', label: '주의 대상', cols: ['keyword', 'target'] },
  { id: 'synonym', label: '동의어', cols: ['word', 'standard', 'syn_type'] },
  { id: 'notice_text', label: '고정 문구', cols: ['code', 'text'] },
]

// 검사 결과 단계 → 배지 (chat이 실제로 하는 일)
const LEVELS = {
  block: { badge: 'taboo', label: '차단', note: 'AI를 부르지 않고 안내 문구만 보여 줘요' },
  redirect: { badge: 'caution', label: '안내로 돌림', note: '약을 골라 달라는 요청이라 약사 상담을 권해요' },
  warn: { badge: 'caution', label: '주의 덧붙임', note: '답변은 하고, 주의 대상 안내를 덧붙여요' },
  pass: { badge: 'none', label: '사전 통과', note: '사전에는 걸린 게 없어요. 실제 AI 질문에서는 다음 단계로 AI가 위험 상황인지 한 번 더 판단해요' },
}

function DictTester() {
  const [question, setQuestion] = useState('')
  const [result, setResult] = useState(null)
  const [error, setError] = useState('')

  const handleTest = async (e) => {
    e.preventDefault()
    setError('')
    try {
      const res = await fetch('/api/admin/dict/test', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question }),
      })
      const data = await res.json().catch(() => ({}))
      if (!res.ok) throw new Error(typeof data.detail === 'string' ? data.detail : '시험하지 못했어요.')
      setResult(data)
    } catch (err) {
      setResult(null)
      setError(err.message)
    }
  }

  const level = result && LEVELS[result.safety.level]
  return (
    <section className="card">
      <h2>문장 시험기</h2>
      <p className="muted">AI 질문의 첫 번째 검사(사전)만 돌려 봐요. 두 번째 검사(AI의 위험 판단)는 하지 않고, 기록도 남기지 않아요. 위험한 문장이 여기서 통과하면 사전에 단어를 더할 후보예요.</p>
      <form onSubmit={handleTest} style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
        <input value={question} onChange={(e) => setQuestion(e.target.value)} maxLength={500}
          placeholder="예: 가슴이 조이고 숨이 차요" style={{ flex: 1, minWidth: 200 }} />
        <button type="submit" className="btn btn-primary" disabled={!question.trim()}>시험</button>
      </form>
      {error && <p style={{ color: 'var(--danger-text)' }}>{error}</p>}
      {level && (
        <div style={{ marginTop: 12 }}>
          <p><Badge type={level.badge}>{level.label}</Badge> {level.note}</p>
          {result.safety.matched.length > 0 && <p>걸린 단어: {result.safety.matched.join(', ')}</p>}
          {result.safety.message && <p>보여 줄 문구: {result.safety.message}</p>}
          <p>찾은 증상: {result.symptom ?? '없음 (동의어 사전에 맞는 단어가 없어요)'}</p>
        </div>
      )}
    </section>
  )
}

function DictTables() {
  const [dicts, setDicts] = useState(null)
  const [error, setError] = useState('')
  const [which, setWhich] = useState('symptom_keyword')
  const [keyword, setKeyword] = useState('')

  useEffect(() => {
    fetch('/api/admin/dict')
      .then(async (res) => {
        const data = await res.json().catch(() => ({}))
        if (!res.ok) throw new Error(typeof data.detail === 'string' ? data.detail : '사전을 불러오지 못했어요.')
        return data
      })
      .then(setDicts)
      .catch((err) => setError(err.message))
  }, [])

  if (error) return <p style={{ color: 'var(--danger-text)' }}>{error}</p>
  if (!dicts) return <p>사전을 불러오는 중...</p>

  const info = DICTS.find(d => d.id === which)
  const rows = dicts[which].filter(row => info.cols.some(c => String(row[c] ?? '').includes(keyword.trim())))
  return (
    <section className="card">
      <h2>사전 보기</h2>
      <p className="muted">지금 DB에 들어 있는 내용이에요. 고치려면 data/dict/*.csv를 PR로 고쳐 주세요.</p>
      <div className="admin-tabs">
        {DICTS.map(d => (
          <button key={d.id} type="button" className={which === d.id ? 'btn btn-primary' : 'btn btn-secondary'}
            onClick={() => setWhich(d.id)}>
            {d.label} ({dicts[d.id].length})
          </button>
        ))}
      </div>
      <input value={keyword} onChange={(e) => setKeyword(e.target.value)} placeholder="사전 안에서 찾기" />
      <div className="table-card">
        <table className="med-table">
          <thead><tr>{info.cols.map(c => <th key={c}>{c}</th>)}</tr></thead>
          <tbody>
            {rows.map((row, i) => (
              <tr key={i} style={row.is_active === false ? { opacity: 0.5 } : undefined}>
                {info.cols.map(c => <td key={c}>{String(row[c] ?? '')}</td>)}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {rows.length === 0 && <p>맞는 줄이 없어요.</p>}
    </section>
  )
}

function AdminDict() {
  return (<>
    <DictTester />
    <DictTables />
  </>)
}
export default AdminDict
