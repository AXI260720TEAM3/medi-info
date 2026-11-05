import { useEffect, useState } from 'react'
import AlertBox from './AlertBox'
import ErrorMessage from './ErrorMessage'
import Loading from './Loading'
import SourceChip from './SourceChip'

// 내 약 함께 먹기 점검: <MedCheck key={횟수} />. 약이 바뀌면 key를 바꿔 다시 점검해요
// 판정별 표시와 경고 종류. 색만으로 구분하지 않게 글자로도 판정을 적어요
const RESULTS = {
  block: { icon: '🔴', type: 'taboo', label: '함께 먹으면 안 돼요' },
  warn: { icon: '🟡', type: 'caution', label: '주의가 필요해요' },
  unknown: { icon: '🟡', type: 'caution', label: '확인을 끝내지 못했어요' },
}

function MedCheck() {
  const [answer, setAnswer] = useState(null)
  const [error, setError] = useState('')
  const [attempt, setAttempt] = useState(0)

  useEffect(() => {
    fetch('/api/my-meds/check')
      .then(async res => {
        if (!res.ok) throw new Error()
        setAnswer(await res.json())
      })
      .catch(() => setError('내 약을 점검하지 못했어요. 잠시 후 다시 시도해 주세요.'))
  }, [attempt])

  const handleRetry = () => {
    setError('')
    setAttempt(attempt + 1)
  }

  if (error) return <ErrorMessage message={error} onRetry={handleRetry} />
  if (answer === null) return <Loading text="내 약을 점검하는 중이에요" />

  const needCheck = answer.results.filter(result => result.level !== 'pass')

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
      {needCheck.length === 0 && (
        <AlertBox type="info" title="⚪ 확인된 병용금기나 성분 겹침은 없어요." />
      )}
      {needCheck.length > 0 && <p className="card-title">확인 필요 {needCheck.length}건</p>}
      {needCheck.map(result => {
        const shown = RESULTS[result.level]
        return (
          <AlertBox
            key={`${result.item_seq_a}-${result.item_seq_b}`}
            type={shown.type}
            title={`${shown.icon} ${result.item_name_a} + ${result.item_name_b}: ${shown.label}`}
          >
            {result.reasons.map(reason => <p key={reason}>{reason}</p>)}
            {result.basis.length > 0 && (
              <p style={{ marginTop: 8 }}>
                <SourceChip>판정 근거: {result.basis.join(' · ')}</SourceChip>
              </p>
            )}
          </AlertBox>
        )
      })}
      <p className="muted">
        식약처 자료에서 찾지 못한 조합이라도 문제가 없다는 뜻은 아니에요. 진단이나 처방이 아니에요. 복용 전에 약사와 상의하세요.
      </p>
    </div>
  )
}
export default MedCheck
