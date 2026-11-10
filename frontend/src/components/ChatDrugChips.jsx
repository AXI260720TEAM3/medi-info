import { useState } from 'react'
import { baseName } from '../utils/image'

// AI 질문의 "이 대화의 약" (E안, API 계약 6장): <ChatDrugChips drugs={[...]} currentSeq={...} ... />
// - 칩을 누르면 지금 약(●)이 바뀌고, ×를 누르면 목록에서 빠져요
// - [+ 약 추가]는 약 이름 검색(GET /api/drugs, 전문의약품 포함)으로 담아요. 질문 없이도 담을 수 있어요
// - 목록은 이 화면에만 있고 저장하지 않아요 (저장은 내 약에서)
export const MAX_DRUGS = 10

function ChatDrugChips({ drugs, currentSeq, onSelect, onRemove, onAdd, notice, disabled }) {
  const [open, setOpen] = useState(false)
  const [query, setQuery] = useState('')
  const [results, setResults] = useState(null)
  const [searching, setSearching] = useState(false)
  const [error, setError] = useState('')

  const handleSearch = async (event) => {
    event.preventDefault()
    const q = query.trim()
    if (!q) return
    setSearching(true)
    setError('')
    try {
      const res = await fetch(`/api/drugs?q=${encodeURIComponent(q)}&page=1`)
      if (!res.ok) throw new Error()
      const data = await res.json()
      setResults(data.items)
    } catch {
      setResults(null)
      setError('약을 찾지 못했어요. 잠시 후 다시 시도해 주세요.')
    } finally {
      setSearching(false)
    }
  }

  const handleAdd = (drug) => {
    onAdd({ item_seq: drug.item_seq, item_name: drug.item_name })
    setOpen(false)
    setQuery('')
    setResults(null)
  }

  const inList = new Set(drugs.map(d => d.item_seq))
  const full = drugs.length >= MAX_DRUGS

  return (
    <div className="card drug-chips-card" aria-label="이 대화의 약">
      <p className="muted" style={{ margin: 0 }}>
        이 대화의 약 {drugs.length > 0 && `(${drugs.length}개)`} · ●는 지금 이야기하는 약이에요
      </p>

      <div className="drug-chips">
        {drugs.length === 0 && (
          <span className="muted">아직 없어요. 질문에 약 이름을 쓰거나 [+ 약 추가]로 담아 주세요.</span>
        )}
        {drugs.map(drug => {
          const current = drug.item_seq === currentSeq
          return (
            <span key={drug.item_seq} className={current ? 'drug-chip is-current' : 'drug-chip'}>
              <button
                type="button"
                className="drug-chip-name"
                aria-pressed={current}
                onClick={() => onSelect(drug.item_seq)}
                disabled={disabled}
                title={drug.item_name}
              >
                {current && <span aria-hidden="true">● </span>}
                {baseName(drug.item_name || drug.item_seq)}
              </button>
              <button
                type="button"
                className="drug-chip-remove"
                aria-label={`${baseName(drug.item_name || drug.item_seq)} 빼기`}
                onClick={() => onRemove(drug.item_seq)}
                disabled={disabled}
              >
                ×
              </button>
            </span>
          )
        })}
        <button
          type="button"
          className="btn btn-secondary drug-chip-add"
          onClick={() => setOpen(!open)}
          disabled={disabled || full}
          aria-expanded={open}
        >
          {open ? '닫기' : '+ 약 추가'}
        </button>
      </div>

      {full && <p className="muted" style={{ margin: 0 }}>약은 {MAX_DRUGS}개까지 담을 수 있어요. 하나를 빼면 더 담을 수 있어요.</p>}
      {notice && <p className="muted" style={{ margin: 0 }} role="status">{notice}</p>}

      {open && (
        <div className="drug-chip-picker">
          <form onSubmit={handleSearch} style={{ display: 'flex', gap: 8 }}>
            <input
              className="input"
              aria-label="담을 약 이름"
              placeholder="약 이름 (예: 타이레놀)"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              style={{ flex: 1, minWidth: 0 }}
            />
            <button type="submit" className="btn btn-primary" disabled={searching || !query.trim()}>찾기</button>
          </form>
          {searching && <p className="muted" style={{ margin: 0 }}>찾는 중이에요…</p>}
          {error && <p className="muted" style={{ margin: 0 }}>{error}</p>}
          {results && results.length === 0 && <p className="muted" style={{ margin: 0 }}>찾은 약이 없어요. 이름을 다시 확인해 주세요.</p>}
          {results && results.length > 0 && (
            <div className="drug-chips">
              {results.map(drug => (
                <button
                  key={drug.item_seq}
                  type="button"
                  className="drug-chip is-candidate"
                  onClick={() => handleAdd(drug)}
                  disabled={inList.has(drug.item_seq)}
                  title={drug.item_name}
                >
                  {baseName(drug.item_name)}{inList.has(drug.item_seq) ? ' (담음)' : ''}
                </button>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
export default ChatDrugChips
