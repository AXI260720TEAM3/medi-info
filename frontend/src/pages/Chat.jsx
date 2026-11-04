import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router'

const API_URL = import.meta.env.VITE_API_URL || '/api/ask'
const HISTORY_LIMIT = 6

function initialDrugContext() {
  const params = new URLSearchParams(window.location.search)
  return {
    itemSeq: params.get('itemSeq') || params.get('item_seq') || null,
    drugName: params.get('drugName') || params.get('drug_name') || null,
  }
}

export default function Chat() {
  const [drug, setDrug] = useState(initialDrugContext)
  const [messages, setMessages] = useState([])
  const [draft, setDraft] = useState('')
  const [pendingQuestion, setPendingQuestion] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const bottomRef = useRef(null)
  const requestInFlight = useRef(false)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' })
  }, [messages, pendingQuestion, error])

  async function handleSubmit(event) {
    event.preventDefault()
    const question = draft.trim()
    if (!question || requestInFlight.current) return

    requestInFlight.current = true
    setLoading(true)
    setError('')
    setPendingQuestion(question)

    // 현재 질문은 question에 별도로 전송하므로 history에는 이전 대화만 넣습니다.
    const history = messages.slice(-HISTORY_LIMIT).map(({ role, content }) => ({
      role,
      content: content.slice(0, 700),
    }))

    try {
      const response = await fetch(API_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          question,
          drug_name: drug.drugName,
          item_seq: drug.itemSeq,
          history,
        }),
      })

      let result
      try {
        result = await response.json()
      } catch {
        throw new Error('서버 응답을 읽을 수 없어요.')
      }

      if (!response.ok) {
        const detail = typeof result?.detail === 'string' ? result.detail : ''
        throw new Error(
          response.status === 503
            ? '의약품 정보 또는 AI 서버가 응답하지 않아요. 다시 시도해 주세요.'
            : detail || `요청을 처리하지 못했어요. (HTTP ${response.status})`,
        )
      }

      if (typeof result.answer !== 'string' || !result.answer.trim()) {
        throw new Error('AI 답변이 비어 있어요. 다시 시도해 주세요.')
      }

      setMessages((prev) => [
        ...prev,
        { role: 'user', content: question },
        {
          role: 'assistant',
          content: result.answer,
          source: result.source || '',
          risk: result.risk || '',
          category: result.category || '',
          items: result.items || [],
          itemsNote: result.items_note || '',
        },
      ])
      setDrug((prev) => ({
        itemSeq: result.item_seq || prev.itemSeq,
        drugName: result.item_name || prev.drugName,
      }))
      setDraft('')
    } catch (err) {
      setError(err instanceof Error ? err.message : '알 수 없는 오류가 발생했어요.')
      // 실패한 질문은 대화 이력에 넣지 않고 입력란에 남겨 재시도하게 합니다.
    } finally {
      setPendingQuestion('')
      setLoading(false)
      requestInFlight.current = false
    }
  }

  return (
    <section style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      <header>
        <h1 className="title">AI 의약품 질문</h1>
        <p className="muted">
          {drug.drugName
            ? `선택한 의약품: ${drug.drugName}`
            : drug.itemSeq
              ? `선택한 의약품 품목번호: ${drug.itemSeq}`
              : '의약품을 선택하지 않았어요. 질문에 약 이름을 포함해 주세요.'}
        </p>
      </header>

      <div className="card" aria-label="채팅 대화" style={{ display: 'flex', flexDirection: 'column', gap: 12, minHeight: 280 }}>
        {messages.length === 0 && !pendingQuestion && (
          <p className="muted">의약품의 효능, 복용방법, 주의사항 등을 질문해 보세요.</p>
        )}
        {messages.map((message, index) => (
          <div
            key={index}
            style={{
              alignSelf: message.role === 'user' ? 'flex-end' : 'flex-start',
              maxWidth: '90%',
              padding: '12px 14px',
              border: '1px solid var(--border)',
              borderRadius: 'var(--radius)',
              background: message.role === 'user' ? 'var(--primary-bg)' : 'var(--surface)',
              whiteSpace: 'pre-wrap',
              overflowWrap: 'anywhere',
            }}
          >
          {message.role === 'assistant' &&
            message.risk === '위험 상황' && (
              <strong>긴급 안내</strong>
            )}

          <div>{message.content}</div>

          {message.itemsNote && (
            <div style={{ marginTop: 8 }}>
              <p className="muted" style={{ marginTop: 0, marginBottom: 4 }}>{message.itemsNote}</p>
              {message.items.length > 0 && (
                <ul style={{ marginTop: 0, marginBottom: 4 }}>
                  {message.items.map(item => (
                    <li key={item.item_seq}>
                      <Link to={`/drugs/${item.item_seq}`}>{item.item_name}</Link>
                      <span className="muted"> · {item.entp_name}</span>
                    </li>
                  ))}
                </ul>
              )}
              <Link to="/drugs">약 찾기로 가기</Link>
            </div>
          )}

          {message.role === 'assistant' &&
            message.source &&
            message.source !== '안전 사전' &&
            message.risk !== '위험 상황' && (
              <p className="muted" style={{ marginBottom: 0, marginTop: 8 }}>
                출처: {message.source}
              </p>
            )}
        </div>
      ))}

        {pendingQuestion && (
          <div style={{ alignSelf: 'flex-end', maxWidth: '90%', padding: '12px 14px', background: 'var(--primary-bg)', borderRadius: 'var(--radius)', whiteSpace: 'pre-wrap' }}>
            {pendingQuestion}
          </div>
        )}
        {loading && <p className="muted" role="status">답변을 만드는 중이에요…</p>}
        <div ref={bottomRef} />
      </div>

      {error && (
        <div className="card" role="alert" style={{ background: 'var(--surface-muted)' }}>
          <p style={{ margin: 0 }}>{error}</p>
          <p className="muted" style={{ marginBottom: 0 }}>입력한 질문은 유지되어 있어요. 다시 전송할 수 있습니다.</p>
        </div>
      )}

      <form onSubmit={handleSubmit} style={{ display: 'flex', gap: 8 }}>
        <input
          className="input"
          aria-label="의약품 질문 입력"
          placeholder="의약품에 대해 질문하세요"
          value={draft}
          onChange={(event) => setDraft(event.target.value)}
          disabled={loading}
          maxLength={1000}
          style={{ flex: 1, minWidth: 0, minHeight: 44 }}
        />
        <button type="submit" className="btn btn-primary" disabled={loading || !draft.trim()}>
          전송
        </button>
      </form>
      <p className="muted" style={{ marginTop: 0 }}>
        이 답변은 진단이나 처방이 아니에요. 현재 대화는 이 화면에서만 유지됩니다.
      </p>
    </section>
  )
}
