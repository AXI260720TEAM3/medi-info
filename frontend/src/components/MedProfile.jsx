import { useEffect, useState } from 'react'
import AlertBox from './AlertBox'
import ErrorMessage from './ErrorMessage'
import Loading from './Loading'
import SourceChip from './SourceChip'
import TermNotes from './TermNotes'

// 복용자 프로필: <MedProfile checkKey={횟수} onChange={함수} />
const OPTIONS = [
  { target: '없음', label: '선택 안 함' },
  { target: '임부', label: '임신' },
  { target: '소아', label: '소아' },
  { target: '노인', label: '노인' },
]

// 프로필에 맞는 식약처 DUR 주의 자료. 자료가 없어도 안전하다는 뜻이 아니라고 함께 알려요
function ProfileCautions() {
  const [answer, setAnswer] = useState(null)
  const [error, setError] = useState('')
  const [attempt, setAttempt] = useState(0)

  useEffect(() => {
    fetch('/api/my-meds/cautions')
      .then(async res => {
        if (!res.ok) throw new Error()
        setAnswer(await res.json())
      })
      .catch(() => setError('프로필 주의사항을 불러오지 못했어요. 잠시 후 다시 시도해 주세요.'))
  }, [attempt])

  const handleRetry = () => {
    setError('')
    setAttempt(attempt + 1)
  }

  if (error) return <ErrorMessage message={error} onRetry={handleRetry} />
  if (answer === null) return <Loading text="프로필 주의사항을 찾는 중이에요" />

  const found = answer.results.filter(result => result.cautions?.length > 0)
  const failed = answer.results.filter(result => result.cautions === null)

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
      {found.map(result => {
        const taboo = result.cautions[0].type.includes('금기')
        return (
          <AlertBox
            key={result.item_seq}
            type={taboo ? 'taboo' : 'caution'}
            title={`${taboo ? '🔴' : '🟡'} ${result.item_name}: ${result.cautions[0].type}`}
          >
            {result.cautions.map(caution => (
              <p key={`${caution.ingredient}-${caution.content}`}>
                {caution.ingredient && <strong>{caution.ingredient} 성분 </strong>}
                {caution.content}
              </p>
            ))}
            <TermNotes texts={result.cautions.map(caution => caution.content)} />
            <p style={{ marginTop: 8 }}><SourceChip>출처: 식약처 DUR</SourceChip></p>
          </AlertBox>
        )
      })}
      {failed.length > 0 && (
        <AlertBox type="caution" title="🟡 일부 약의 주의사항을 확인하지 못했어요">
          <p>{failed.map(result => result.item_name).join(', ')}</p>
        </AlertBox>
      )}
      <p className="muted">
        {answer.notice} 식약처 DUR 자료에 없어도 안전하다는 뜻은 아니에요.
      </p>
    </div>
  )
}

function MedProfile({ checkKey, onChange }) {
  const [target, setTarget] = useState(null)
  const [saveError, setSaveError] = useState('')
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    fetch('/api/my-meds/profile')
      .then(res => (res.ok ? res.json() : { target: '없음' }))
      .then(data => setTarget(data.target))
      .catch(() => setTarget('없음'))
  }, [])

  const handleChoose = async (next) => {
    setSaveError('')
    setSaving(true)
    try {
      const res = await fetch('/api/my-meds/profile', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ target: next }),
      })
      if (!res.ok) throw new Error()
      setTarget(next)
      onChange()
    } catch {
      setSaveError('프로필을 저장하지 못했어요. 잠시 후 다시 시도해 주세요.')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
      <div className="card">
        <p className="card-title">복용자 프로필</p>
        <p className="muted">임신 중이거나 아이, 어르신이 먹는 약이면 프로필을 고르세요. 해당 주의사항을 먼저 보여 드려요.</p>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
          {OPTIONS.map(option => (
            <button
              key={option.target}
              type="button"
              className={`btn ${target === option.target ? 'btn-primary' : 'btn-secondary'}`}
              aria-pressed={target === option.target}
              disabled={saving || target === null}
              onClick={() => handleChoose(option.target)}
            >
              {option.label}
            </button>
          ))}
        </div>
      </div>
      {saveError && <ErrorMessage message={saveError} />}
      {target !== null && target !== '없음' && <ProfileCautions key={`${target}-${checkKey}`} />}
    </div>
  )
}
export default MedProfile
