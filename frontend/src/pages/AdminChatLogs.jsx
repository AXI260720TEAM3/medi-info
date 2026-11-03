
import { useEffect, useState } from 'react'

function AdminChatLogs() {
  const [logs, setLogs] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    fetch('/api/admin/chat-logs?limit=50')
      .then(async (res) => {
        const data = await res.json()
        if (!res.ok) {
          throw new Error(data.detail || '기록을 불러오지 못했어요.')
        }
        return data
      })
      .then((data) => setLogs(data.items))
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false))
  }, [])

  return (
    <section className="card">
      <h1 className="title">관리자 질문 기록</h1>
      <p className="muted">최근 질문 50개를 확인할 수 있어요.</p>

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
            {log.blocked && <span> · 차단</span>}
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
