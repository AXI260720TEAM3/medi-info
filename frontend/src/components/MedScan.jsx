import { useState } from 'react'
import AlertBox from './AlertBox'
import ErrorMessage from './ErrorMessage'
import Loading from './Loading'

// 약봉지 사진으로 내 약 추가: <MedScan onAdded={함수} />
// AI가 읽은 이름은 틀릴 수 있어서, 허가정보에서 찾은 후보를 사용자가 직접 골라야 내 약에 넣어요
const MAX_BYTES = 20 * 1024 * 1024  // 고르는 원본 사진. 보낼 때는 줄여서 보내요
const MAX_SIDE = 1600  // 사진을 읽는 AI는 한 번에 받을 수 있는 양이 정해져 있어서, 폰 사진(4000px)은 그대로 보내면 거절해요
const SKIP = 'skip'

// '게보린정(수출명:돌로린정)' -> '게보린정'
const baseName = itemName => itemName.split('(')[0].trim()

// 긴 쪽이 MAX_SIDE를 넘으면 줄여서 JPG 글자(data:image/jpeg;base64,...)로 바꿔요
function shrinkImage(file) {
  return new Promise((resolve, reject) => {
    const url = URL.createObjectURL(file)
    const img = new Image()
    img.onload = () => {
      const scale = Math.min(1, MAX_SIDE / Math.max(img.width, img.height))
      const canvas = document.createElement('canvas')
      canvas.width = Math.round(img.width * scale)
      canvas.height = Math.round(img.height * scale)
      canvas.getContext('2d').drawImage(img, 0, 0, canvas.width, canvas.height)
      URL.revokeObjectURL(url)
      resolve(canvas.toDataURL('image/jpeg', 0.9))
    }
    img.onerror = () => {
      URL.revokeObjectURL(url)
      reject(new Error('사진 열기 실패'))
    }
    img.src = url
  })
}

function MedScan({ onAdded }) {
  const [results, setResults] = useState(null)
  const [picked, setPicked] = useState({})   // 읽은 이름 번호 -> 고른 품목번호 (또는 SKIP)
  const [scanning, setScanning] = useState(false)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')

  const handleFile = async (event) => {
    const file = event.target.files[0]
    event.target.value = ''  // 같은 사진을 다시 골라도 동작하게
    if (!file) return
    setError('')
    setMessage('')
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
        setError(data.detail || failed)  // 서버가 보낸 한국어 안내 (사진이 너무 커요, AI가 응답하지 않아요 …)
        return
      }
      // 이름이 똑같은 약을 찾은 줄만 미리 골라 두고, 비슷한 후보만 있는 줄은 사용자가 고르게 해요
      const first = {}
      data.results.forEach((result, i) => {
        first[i] = result.status === 'found' ? result.candidates[0].item_seq : SKIP
      })
      setPicked(first)
      setResults(data.results)
    } catch {
      setError(failed)
    } finally {
      setScanning(false)
    }
  }

  const chosen = (results || [])
    .map((result, i) => result.candidates.find(drug => drug.item_seq === picked[i]))
    .filter(Boolean)

  const handleSave = async () => {
    setSaving(true)
    setError('')
    let added = 0
    let already = 0
    try {
      for (const drug of chosen) {
        const res = await fetch('/api/my-meds', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ item_seq: drug.item_seq, item_name: baseName(drug.item_name), added_by: '사진' }),
        })
        if (res.status === 201) added += 1
        else if (res.status === 409) already += 1
        else throw new Error()
      }
      setResults(null)
      setMessage(`${added}개를 내 약에 넣었어요.${already ? ` ${already}개는 이미 있던 약이에요.` : ''}`)
    } catch {
      setError(`${added}개까지 넣고 나머지는 넣지 못했어요. 잠시 후 다시 시도해 주세요.`)
    } finally {
      setSaving(false)
      if (added > 0) onAdded()
    }
  }

  return (
    <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
      <div>
        <p className="card-title">약봉지 사진으로 추가</p>
        <p className="muted">
          약 이름이 잘 보이게 찍은 약봉지나 복약안내문 사진을 올리세요. 사진은 저장하지 않아요.
          환자 이름은 가리고 찍어도 돼요.
        </p>
      </div>
      <label className="btn btn-secondary" style={{ alignSelf: 'flex-start' }}>
        사진 고르기
        <input
          type="file"
          accept="image/jpeg,image/png"
          onChange={handleFile}
          disabled={scanning || saving}
          className="sr-only"
        />
      </label>

      {scanning && <Loading text="사진에서 약 이름을 찾는 중이에요. 20초쯤 걸릴 수 있어요" />}
      {error && <ErrorMessage message={error} />}
      {message && <p role="status">{message}</p>}

      {results && results.length === 0 && (
        <AlertBox type="caution" title="🟡 사진에서 약 이름을 찾지 못했어요">
          <p>약 이름이 잘 보이게 가까이에서 다시 찍어 주세요.</p>
        </AlertBox>
      )}

      {results && results.length > 0 && (<>
        <AlertBox type="caution" title="🟡 약봉지와 비교해서 맞는 약을 골라 주세요">
          <p>AI가 사진의 글자를 잘못 읽을 수 있어요. 고른 약만 내 약에 넣어요.</p>
        </AlertBox>
        {results.map((result, i) => (
          <fieldset key={`${i}-${result.read}`} className="card" style={{ margin: 0 }}>
            <legend>사진에서 읽은 글자: <strong>{result.read}</strong></legend>
            {result.status === 'withdrawn' && (
              <p>
                ⚪ <strong>{baseName(result.withdrawn.item_name)}</strong>은(는) {result.withdrawn.cancel_date}에
                허가가 {result.withdrawn.cancel_name}된 약이에요. 지금은 팔지 않아서 내 약에 넣을 수 없어요.
                아직 이 약을 갖고 있다면 복용 전에 약사와 상의하세요.
              </p>
            )}
            {result.status === 'unchecked' && (
              <p className="muted">약 정보 서버가 느려서 확인하지 못했어요. 잠시 후 다시 올리거나 약 검색에서 이름으로 찾아 주세요.</p>
            )}
            {result.status === 'none' && (
              <p className="muted">허가정보에서 찾지 못했어요. 약 검색에서 이름으로 찾아 주세요.</p>
            )}
            {result.candidates.map(drug => (
              <label key={drug.item_seq} style={{ display: 'block', padding: '4px 0' }}>
                <input
                  type="radio"
                  name={`scan-${i}`}
                  checked={picked[i] === drug.item_seq}
                  onChange={() => setPicked({ ...picked, [i]: drug.item_seq })}
                />{' '}
                {baseName(drug.item_name)} <span className="muted">{drug.entp_name}</span>
              </label>
            ))}
            {result.candidates.length > 0 && (
              <label style={{ display: 'block', padding: '4px 0' }}>
                <input
                  type="radio"
                  name={`scan-${i}`}
                  checked={picked[i] === SKIP}
                  onChange={() => setPicked({ ...picked, [i]: SKIP })}
                />{' '}
                여기 없어요 (넣지 않기)
              </label>
            )}
          </fieldset>
        ))}
        <button
          type="button"
          className="btn btn-primary"
          style={{ alignSelf: 'flex-start' }}
          disabled={chosen.length === 0 || saving}
          onClick={handleSave}
        >
          고른 약 {chosen.length}개를 내 약에 넣기
        </button>
      </>)}
    </div>
  )
}
export default MedScan
