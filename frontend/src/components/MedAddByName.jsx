import { useState } from 'react'
import ErrorMessage from './ErrorMessage'
import { baseName } from '../utils/image'

// 약 이름으로 내 약 추가: <MedAddByName onAdded={함수} />
// AI 질문의 [+ 약 추가]와 같은 방식: 이름 검색(GET /api/drugs) → 후보를 눌러 담기(POST /api/my-meds, 추가 방법 "검색")
function MedAddByName({ onAdded, savedSeqs = [] }) {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState(null)
  const [searching, setSearching] = useState(false)
  const [savingSeq, setSavingSeq] = useState('')
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')

  const handleSearch = async (event) => {
    event.preventDefault()
    const q = query.trim()
    if (!q) return
    setSearching(true)
    setError('')
    setMessage('')
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

  const handleAdd = async (drug) => {
    setSavingSeq(drug.item_seq)
    setError('')
    setMessage('')
    try {
      const res = await fetch('/api/my-meds', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ item_seq: drug.item_seq, item_name: baseName(drug.item_name), added_by: '검색' }),
      })
      if (res.status === 409) {
        setMessage(`이미 내 약에 있어요: ${baseName(drug.item_name)}`)
        return
      }
      if (!res.ok) throw new Error()
      setMessage(`내 약에 넣었어요: ${baseName(drug.item_name)}`)
      setResults(null)
      setQuery('')
      onAdded()
    } catch {
      setError('내 약에 넣지 못했어요. 잠시 후 다시 시도해 주세요.')
    } finally {
      setSavingSeq('')
    }
  }

  const saved = new Set(savedSeqs)

  return (
    <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
      <div>
        <p className="card-title">약 이름으로 추가</p>
        <p className="muted">약 이름을 찾아서 눌러 담으세요. 일반약과 처방약 모두 찾을 수 있어요.</p>
      </div>
      <form onSubmit={handleSearch} style={{ display: 'flex', gap: 8 }}>
        <label htmlFor="med-add-name" className="sr-only">담을 약 이름</label>
        <input
          id="med-add-name"
          className="input"
          placeholder="약 이름 (예: 타이레놀)"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          style={{ flex: 1, minWidth: 0 }}
        />
        <button type="submit" className="btn btn-primary" disabled={searching || !query.trim()}>찾기</button>
      </form>

      {searching && <p className="muted" style={{ margin: 0 }} role="status">찾는 중이에요…</p>}
      {error && <ErrorMessage message={error} />}
      {message && <p style={{ margin: 0 }} role="status">{message}</p>}
      {results && results.length === 0 && (
        <p className="muted" style={{ margin: 0 }}>찾은 약이 없어요. 이름을 다시 확인해 주세요.</p>
      )}
      {results && results.length > 0 && (
        <div className="drug-chips">
          {results.map(drug => (
            <button
              key={drug.item_seq}
              type="button"
              className="drug-chip is-candidate"
              onClick={() => handleAdd(drug)}
              disabled={Boolean(savingSeq) || saved.has(drug.item_seq)}
              title={drug.item_name}
            >
              + {baseName(drug.item_name)}{saved.has(drug.item_seq) ? ' (담음)' : ''}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
export default MedAddByName
