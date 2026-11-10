import { useEffect, useState } from 'react'
import Badge from '../components/Badge'

// 거르기 이름은 서버(routes/admin.py FILTERS)와 같아요
const FILTERS = [
  { id: 'all', label: '전체' },
  { id: 'blocked', label: '차단·안내' },
  { id: 'unclassified', label: '분류 못 함' },
  { id: 'reported', label: '신고·도움 안 됨' },
]

function AdminChatLogs() {
  const [only, setOnly] = useState('all')
  const [logs, setLogs] = useState([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  // 거르기를 바꾸면 "불러오는 중"으로 바꾼 뒤 새로 불러요
  const changeFilter = (value) => {
    setOnly(value)
    setLoading(true)
    setError('')
  }

  useEffect(() => {
    fetch(`/api/admin/chat-logs?limit=50&only=${only}`)
      .then(async (res) => {
        const data = await res.json()
        if (!res.ok) {
          throw new Error(data.detail || '기록을 불러오지 못했어요.')
        }
        return data
      })
      .then((data) => { setLogs(data.items); setTotal(data.total) })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false))
  }, [only])

  return (
    <section className="card">
      <h2>질문 기록</h2>
      <label>
        보기{' '}
        <select value={only} onChange={(e) => changeFilter(e.target.value)}>
          {FILTERS.map(f => <option key={f.id} value={f.id}>{f.label}</option>)}
        </select>
      </label>
      <p className="muted">
        {loading ? '' : `${total.toLocaleString()}건 중 최근 ${logs.length}건이에요. `}
        질문은 저장할 때 전화번호 같은 개인정보를 가려 둬요. 90일이 지나면 지워져요.
      </p>

      {loading && <p>기록을 불러오는 중...</p>}
      {error && <p style={{ color: 'var(--danger-text)' }}>{error}</p>}

      {!loading && !error && logs.length === 0 && (
        <p>저장된 질문이 없어요.</p>
      )}

      {!loading && !error && logs.map((log) => (
        <details key={log.log_id} style={{
          padding: 12,
          borderBottom: '1px solid var(--border-color, #ddd)'
        }}>
          <summary style={{ cursor: 'pointer' }}>
            <strong>{log.question}</strong>
            {' '}
            {log.blocked && <Badge type="taboo">{log.block_reason === 'redirect' ? '안내' : '차단'}</Badge>}
            {(log.reported || log.feedback === -1) && <Badge type="caution">신고</Badge>}
          </summary>

          <p><strong>답변:</strong> {log.answer || '없음'}</p>
          <p className="muted">
            분류: {log.question_type || '미분류'}
            {' · '}
            {new Date(log.created_at).toLocaleString('ko-KR')}
          </p>
        </details>
      ))}
    </section>
  )
}

export default AdminChatLogs
