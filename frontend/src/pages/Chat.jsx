import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router'
import ChatDrugChips, { MAX_DRUGS } from '../components/ChatDrugChips'
import ChatScan from '../components/ChatScan'
import OpenPharmacies from '../components/OpenPharmacies'
import { baseName } from '../utils/image'

const API_URL = import.meta.env.VITE_API_URL || '/api/ask'
const HISTORY_LIMIT = 6

// 약 상세의 [이 약 질문하기]는 /chat?item_seq=…&drug_name=… 으로 와요 → 그 약 하나를 담고 ●로
function initialDrugs() {
  const params = new URLSearchParams(window.location.search)
  const itemSeq = params.get('itemSeq') || params.get('item_seq')
  const name = params.get('drugName') || params.get('drug_name')
  return itemSeq ? [{ item_seq: itemSeq, item_name: name || itemSeq }] : []
}

// 목록에 약 담기: 이미 있으면 그대로, 10개가 차면 담지 않아요 (그대로 돌려줘요)
function addTo(list, drug) {
  if (!drug?.item_seq || list.some(d => d.item_seq === String(drug.item_seq))) return list
  if (list.length >= MAX_DRUGS) return list
  return [...list, { item_seq: String(drug.item_seq), item_name: drug.item_name || '' }]
}

// REQ-F-050: 약사 상담을 권하는 답이면 답변 아래에 "지금 문 연 약국"을 붙여요
function needsPharmacy(message, isLast) {
  return message.role === 'assistant'
    && message.content.includes('약사')
    && message.risk !== '위험 상황'
    && isLast
}

export default function Chat() {
  // 이 대화의 약 (API 계약 6장). 목록의 주인은 화면이고, 서버는 "담아라"(add_drugs)·"지금 약"(current_seq)만 알려줘요
  const [drugs, setDrugs] = useState(initialDrugs)
  const [currentSeq, setCurrentSeq] = useState(() => initialDrugs()[0]?.item_seq ?? null)
  const [chipNotice, setChipNotice] = useState('')
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

  // 질문 보내기. list·current를 직접 받아요: 후보 칩을 누른 직후처럼 상태가 아직 안 바뀐 때도 새 목록으로 보내려고
  async function send(question, list, current, fromDraft) {
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
          history,
          drugs: list,
          current_seq: current,
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
          candidates: result.candidates || null,   // 같은 이름의 약이 여럿: 골라서 다시 묻기
          question,
        },
      ])

      // 서버가 질문에서 찾은 약을 담고, 지금 약(●)을 맞춰요 (API 계약 2-2)
      let next = list
      for (const found of result.add_drugs || []) next = addTo(next, found)
      setDrugs(next)
      if (result.current_seq && next.some(d => d.item_seq === result.current_seq)) {
        setCurrentSeq(result.current_seq)
      }
      setChipNotice(
        (result.add_drugs || []).some(d => !next.some(n => n.item_seq === String(d.item_seq)))
          ? `약은 ${MAX_DRUGS}개까지라 새로 찾은 약을 담지 못했어요. 하나를 빼고 다시 물어봐 주세요.`
          : '',
      )
      if (fromDraft) setDraft('')
    } catch (err) {
      setError(err instanceof Error ? err.message : '알 수 없는 오류가 발생했어요.')
      // 실패한 질문은 대화 이력에 넣지 않고 입력란에 남겨 재시도하게 합니다.
    } finally {
      setPendingQuestion('')
      setLoading(false)
      requestInFlight.current = false
    }
  }

  function handleSubmit(event) {
    event.preventDefault()
    send(draft.trim(), drugs, currentSeq, true)
  }

  // 담고 ●로 (후보 칩, 약봉지 사진). 10개가 차서 못 담으면 null
  function pickDrug(drug) {
    const next = addTo(drugs, drug)
    if (next === drugs && !drugs.some(d => d.item_seq === String(drug.item_seq))) {
      setChipNotice(`약은 ${MAX_DRUGS}개까지예요. 하나를 빼고 다시 골라 주세요.`)
      return null
    }
    setDrugs(next)
    setCurrentSeq(String(drug.item_seq))
    setChipNotice('')
    return next
  }

  // [+ 약 추가]: 담기만 해요. 지금 약이 없을 때만 ●로
  function addDrug(drug) {
    setDrugs(addTo(drugs, drug))
    if (!currentSeq) setCurrentSeq(String(drug.item_seq))
  }

  // ×: 빼기. 지금 약을 빼면 남은 약 중 마지막 약이 ●
  function removeDrug(seq) {
    const next = drugs.filter(d => d.item_seq !== seq)
    setDrugs(next)
    if (seq === currentSeq) setCurrentSeq(next.length ? next[next.length - 1].item_seq : null)
    setChipNotice('')
  }

  // 후보를 고르면 그 약을 담고, 방금 질문을 그 약으로 다시 물어요 ("게보린 공복에…" → 게보린정)
  function pickCandidate(message, candidate) {
    const next = pickDrug(candidate)
    if (next && message.question) send(message.question, next, String(candidate.item_seq), false)
  }

  return (
    <section style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      <header>
        <h1 className="title">AI 의약품 질문</h1>
        <p className="muted">질문에 약 이름을 쓰면 아래 목록에 담겨요. 약을 여러 개 담아 두고 골라 가며 물어볼 수 있어요.</p>
      </header>

      <ChatDrugChips
        drugs={drugs}
        currentSeq={currentSeq}
        onSelect={setCurrentSeq}
        onRemove={removeDrug}
        onAdd={addDrug}
        notice={chipNotice}
        disabled={loading}
      />

      <ChatScan selectedSeq={currentSeq} onPick={(d) => pickDrug({ item_seq: d.itemSeq, item_name: d.drugName })} />

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

          {needsPharmacy(message, index === messages.length - 1) && <OpenPharmacies />}

          {/* 같은 이름의 약이 여럿 (API 계약 2-2 candidates): 고르면 그 약을 담고 방금 질문을 다시 물어요 */}
          {message.candidates?.length > 0 && (
            <div style={{ marginTop: 8, whiteSpace: 'normal' }}>
              <p className="muted" style={{ marginTop: 0, marginBottom: 6 }}>어느 약인가요? 누르면 그 약으로 다시 물어볼게요.</p>
              <div className="drug-chips">
                {message.candidates.map(candidate => (
                  <button
                    key={candidate.item_seq}
                    type="button"
                    className="drug-chip is-candidate"
                    onClick={() => pickCandidate(message, candidate)}
                    disabled={loading}
                    title={candidate.item_name}
                  >
                    {baseName(candidate.item_name)}
                  </button>
                ))}
              </div>
            </div>
          )}

          {message.itemsNote && !message.candidates?.length && (
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
