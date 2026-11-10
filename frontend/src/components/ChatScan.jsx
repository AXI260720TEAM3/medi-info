import { useEffect, useState } from 'react'
import ErrorMessage from './ErrorMessage'
import Loading from './Loading'
import { MAX_BYTES, baseName, shrinkImage } from '../utils/image'

// AI 질문 화면에서 약봉지 사진으로 질문할 약 고르기: <ChatScan selectedSeq={품목번호} onPick={함수} />
// 사진에서 읽은 약을 버튼으로 보여 주고, 누른 약 하나를 채팅의 '선택한 의약품'으로 넘겨요
// 사진 읽기 API(/api/my-meds/scan)는 로그인 + 건강정보 동의가 필요해서, 그런 사람에게만 버튼을 보여 줘요
function ChatScan({ selectedSeq, onPick }) {
  const [canScan, setCanScan] = useState(false)
  const [results, setResults] = useState(null)
  const [scanning, setScanning] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    fetch('/api/auth/me')
      .then(res => (res.ok ? res.json() : null))
      .then(user => setCanScan(Boolean(user?.agree_health)))
      .catch(() => setCanScan(false))
  }, [])

  const handleFile = async (event) => {
    const file = event.target.files[0]
    event.target.value = ''  // 같은 사진을 다시 골라도 동작하게
    if (!file) return
    setError('')
    setResults(null)
    if (file.size > MAX_BYTES) {
      setError('사진이 너무 커요. 20MB 이하로 올려 주세요.')
      return
    }
    setScanning(true)
    const failed = '사진을 읽지 못했어요. 잠시 후 다시 시도해 주세요.'
    try {
      const res = await fetch('/api/my-meds/scan', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ image: await shrinkImage(file) }),
      })
      const data = await res.json().catch(() => ({}))
      if (!res.ok) {
        setError(data.detail || failed)
        return
      }
      setResults(data.results)
    } catch {
      setError(failed)
    } finally {
      setScanning(false)
    }
  }

  if (!canScan) return null

  return (
    <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
        <label className="btn btn-secondary">
          📷 약봉지 사진으로 약 고르기
          <input
            type="file"
            accept="image/jpeg,image/png"
            onChange={handleFile}
            disabled={scanning}
            className="sr-only"
          />
        </label>
        <span className="muted">사진은 저장하지 않아요.</span>
      </div>

      {scanning && <Loading text="사진에서 약 이름을 찾는 중이에요. 20초쯤 걸릴 수 있어요" />}
      {error && <ErrorMessage message={error} />}

      {results && results.length === 0 && (
        <p className="muted" style={{ margin: 0 }}>사진에서 약 이름을 찾지 못했어요. 약 이름이 잘 보이게 가까이에서 다시 찍어 주세요.</p>
      )}

      {results && results.length > 0 && (<>
        <p className="muted" style={{ margin: 0 }}>
          질문할 약을 하나 누르세요. AI가 글자를 잘못 읽을 수 있으니 약봉지와 이름을 비교해 주세요.
        </p>
        {results.map((result, i) => (
          <div key={`${i}-${result.read}`}>
            <p className="muted" style={{ margin: '4px 0' }}>
              사진에서 읽은 글자: <strong>{result.read}</strong>
              {result.status === 'candidates' && ' (비슷한 약 후보)'}
            </p>
            {result.status === 'withdrawn' && (
              <p style={{ margin: 0 }}>
                ⚪ <strong>{baseName(result.withdrawn.item_name)}</strong>은(는) 허가가 {result.withdrawn.cancel_name}된 약이에요.
                복용 전에 약사와 상의하세요.
              </p>
            )}
            {result.status === 'none' && <p className="muted" style={{ margin: 0 }}>허가정보에서 찾지 못했어요.</p>}
            {result.status === 'unchecked' && <p className="muted" style={{ margin: 0 }}>약 정보 서버가 느려서 확인하지 못했어요.</p>}
            <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
              {result.candidates.map(drug => (
                <button
                  key={drug.item_seq}
                  type="button"
                  className={drug.item_seq === selectedSeq ? 'btn btn-primary' : 'btn btn-secondary'}
                  aria-pressed={drug.item_seq === selectedSeq}
                  onClick={() => onPick({ itemSeq: drug.item_seq, drugName: baseName(drug.item_name) })}
                >
                  {baseName(drug.item_name)}
                </button>
              ))}
            </div>
          </div>
        ))}
      </>)}
    </div>
  )
}
export default ChatScan
