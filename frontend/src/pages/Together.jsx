import { useEffect, useState } from 'react'
import { Link } from 'react-router'
import ErrorMessage from '../components/ErrorMessage'
import Loading from '../components/Loading'

// 판정별 제목과 색 (색 조합은 StyleGuide의 금기 · 주의 · 안내)
const RESULTS = {
  block: {
    title: '함께 먹으면 안 되는 조합이에요.',
    style: { background: 'var(--danger-bg)', border: '1.5px solid var(--danger)', color: 'var(--danger-text)' },
  },
  warn: {
    title: '함께 먹을 때 주의가 필요해요.',
    style: { background: 'var(--caution-bg)', border: '1.5px solid var(--caution)', color: 'var(--caution-text)' },
  },
  pass: {
    title: '확인된 병용금기나 성분 겹침은 없어요.',
    style: { background: 'var(--info-bg)', border: '1px solid var(--info-border)', color: 'var(--info-text)' },
  },
}

function Together() {
  const [meds, setMeds] = useState(null)
  const [needLogin, setNeedLogin] = useState(false)
  const [error, setError] = useState('')
  const [seqA, setSeqA] = useState('')
  const [seqB, setSeqB] = useState('')
  const [result, setResult] = useState(null)
  const [checking, setChecking] = useState(false)
  const [checkError, setCheckError] = useState('')

  useEffect(() => {
    fetch('/api/my-meds')
      .then(async res => {
        if (res.status === 401) {
          setNeedLogin(true)
          return
        }
        if (!res.ok) throw new Error()
        setMeds(await res.json())
      })
      .catch(() => setError('내 약을 불러오지 못했어요. 잠시 후 다시 시도해 주세요.'))
  }, [])

  // 약을 바꾸면 이전 결과는 지워요 (다른 약의 결과로 착각하지 않게)
  const clearResult = () => {
    setResult(null)
    setCheckError('')
  }

  const handleCheck = async () => {
    clearResult()
    setChecking(true)
    try {
      const res = await fetch(`/api/together?a=${seqA}&b=${seqB}`)
      if (!res.ok) throw new Error()
      setResult(await res.json())
    } catch {
      setCheckError('확인하지 못했어요. 잠시 후 다시 시도해 주세요.')
    } finally {
      setChecking(false)
    }
  }

  if (needLogin) {
    return <p>함께 먹기 확인은 로그인하면 쓸 수 있어요. <Link to="/login">로그인하기</Link></p>
  }
  if (error) return <ErrorMessage message={error} />
  if (meds === null) return <Loading />
  if (meds.length < 2) {
    return <p>약을 두 개 이상 등록하면 확인할 수 있어요. <Link to="/drugs">약 찾기</Link></p>
  }

  const canCheck = seqA !== '' && seqB !== '' && seqA !== seqB && !checking
  const shown = result && RESULTS[result.level]

  return (<>
    <h1 className="title">함께 먹기 확인</h1>
    <p className="muted">내 약 중 두 개를 골라 함께 먹어도 되는지 확인해요.</p>

    <select className="input" value={seqA} disabled={checking} onChange={e => { setSeqA(e.target.value); clearResult() }}>
      <option value="">첫 번째 약을 고르세요</option>
      {meds.map(med => <option key={med.med_id} value={med.item_seq}>{med.item_name}</option>)}
    </select>

    <select className="input" value={seqB} disabled={checking} onChange={e => { setSeqB(e.target.value); clearResult() }}>
      <option value="">두 번째 약을 고르세요</option>
      {meds.map(med => <option key={med.med_id} value={med.item_seq}>{med.item_name}</option>)}
    </select>

    {seqA !== '' && seqA === seqB && <p className="muted">서로 다른 약을 골라 주세요.</p>}

    <button type="button" className="btn btn-primary" disabled={!canCheck} onClick={handleCheck}>
      확인하기
    </button>

    {checking && <Loading text="확인하는 중이에요" />}
    {checkError && <ErrorMessage message={checkError} />}

    {shown && (
      <div role="status" style={{ ...shown.style, padding: '12px 14px', borderRadius: 12 }}>
        <p style={{ fontWeight: 700 }}>{shown.title}</p>
        {result.reasons.map(reason => <p key={reason}>{reason}</p>)}
        <p>진단이나 처방이 아니에요. 복용 전에 약사와 상의하세요.</p>
      </div>
    )}
  </>)
}
export default Together
