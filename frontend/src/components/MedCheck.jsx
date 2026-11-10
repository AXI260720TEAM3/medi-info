import { useEffect, useState } from 'react'
import ErrorMessage from './ErrorMessage'
import Loading from './Loading'
import MedCheckResult from './MedCheckResult'

// 내 약 함께 먹기 점검: <MedCheck key={횟수} />. 약이 바뀌면 key를 바꿔 다시 점검해요
// 불러오기만 여기서 하고, 결과 카드는 MedCheckResult가 그려요 (AI 질문도 같은 카드를 써요)
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

  return <MedCheckResult answer={answer} />
}
export default MedCheck
