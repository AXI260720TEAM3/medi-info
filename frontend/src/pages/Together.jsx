import { useEffect, useState } from 'react'
import { Link } from 'react-router'
import AlertBox from '../components/AlertBox'
import ErrorMessage from '../components/ErrorMessage'
import Loading from '../components/Loading'

// 판정별 표시와 경고 종류. 색만으로 구분하지 않게 글자로도 판정을 적어요
const RESULTS = {
  block: { icon: '🔴', type: 'taboo', label: '함께 먹으면 안 돼요' },
  warn: { icon: '🟡', type: 'caution', label: '주의가 필요해요' },
  unknown: { icon: '🟡', type: 'caution', label: '확인을 끝내지 못했어요' },
  pass: { icon: '⚪', type: 'info', label: '확인된 문제가 없어요' },
}

const SUMMARIES = {
  block: '함께 먹으면 안 되는 조합이 있어요.',
  warn: '함께 먹을 때 주의가 필요한 조합이 있어요.',
  unknown: '확인을 끝내지 못한 조합이 있어요.',
  pass: '확인된 병용금기나 성분 겹침은 없어요.',
}

function Together() {
  const [answer, setAnswer] = useState(null)
  const [needLogin, setNeedLogin] = useState(false)
  const [needConsent, setNeedConsent] = useState(false)
  const [error, setError] = useState('')
  const [attempt, setAttempt] = useState(0)

  useEffect(() => {
    fetch('/api/my-meds/check')
      .then(async res => {
        if (res.status === 401) {
          setNeedLogin(true)
          return
        }
        if (res.status === 403) {
          setNeedConsent(true)
          return
        }
        if (!res.ok) throw new Error()
        setAnswer(await res.json())
      })
      .catch(() => setError('내 약을 점검하지 못했어요. 잠시 후 다시 시도해 주세요.'))
  }, [attempt])

  const handleRetry = () => {
    setError('')
    setAttempt(attempt + 1)
  }

  if (needLogin) {
    return <p>함께 먹기 확인은 로그인하면 쓸 수 있어요. <Link to="/login">로그인하기</Link></p>
  }
  if (needConsent) {
    return <p>함께 먹기 확인은 건강정보 수집에 동의하면 쓸 수 있어요. <Link to="/account">동의하러 가기</Link></p>
  }
  if (error) return <ErrorMessage message={error} onRetry={handleRetry} />
  if (answer === null) return <Loading text="내 약을 점검하는 중이에요" />
  if (answer.results.length === 0) {
    return <p>약을 두 개 이상 등록하면 확인할 수 있어요. <Link to="/drugs">약 찾기</Link></p>
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
      <h1 className="title">함께 먹기 확인</h1>
      <p className="muted">내 약을 두 개씩 모두 비교했어요.</p>

      <p className="card-title">{RESULTS[answer.level].icon} {SUMMARIES[answer.level]}</p>

      {answer.results.map(result => {
        const shown = RESULTS[result.level]
        return (
          <AlertBox
            key={`${result.item_seq_a}-${result.item_seq_b}`}
            type={shown.type}
            title={`${shown.icon} ${result.item_name_a} + ${result.item_name_b}: ${shown.label}`}
          >
            {result.reasons.map(reason => <p key={reason}>{reason}</p>)}
          </AlertBox>
        )
      })}

      <p className="muted">진단이나 처방이 아니에요. 복용 전에 약사와 상의하세요.</p>
    </div>
  )
}
export default Together
