
import { useState } from 'react'

function MedHistoryForm({ meds, onSaved }) {
  const [medId, setMedId] = useState('')
  const [startDate, setStartDate] = useState('')
  const [timesPerDay, setTimesPerDay] = useState('')
  const [durationDays, setDurationDays] = useState('')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')

  const handleSubmit = async (event) => {
    event.preventDefault()
    setError('')
    setNotice('')
    setSaving(true)

    try {
      const res = await fetch('/api/med-history', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          med_id: Number(medId),
          start_date: startDate,
          times_per_day: timesPerDay === '' ? null : Number(timesPerDay),
          duration_days: durationDays === '' ? null : Number(durationDays),
        }),
      })

      if (!res.ok) {
        const data = await res.json().catch(() => ({}))
        throw new Error(
          typeof data.detail === 'string'
            ? data.detail
            : '복용이력을 저장하지 못했어요.'
        )
      }

      setMedId('')
      setStartDate('')
      setTimesPerDay('')
      setDurationDays('')
      setNotice('복용이력을 저장했어요.')
      onSaved?.()
    } catch (err) {
      setError(err.message || '저장 중 오류가 발생했어요.')
    } finally {
      setSaving(false)
    }
  }

  if (meds.length === 0) {
    return <p className="muted">먼저 내 약에 약을 등록해 주세요.</p>
  }

  return (
    <form onSubmit={handleSubmit}>
      <h3>복용 시작 기록</h3>

      <div>
        <label htmlFor="history-med">약 선택</label>
        <select
          id="history-med"
          value={medId}
          onChange={event => setMedId(event.target.value)}
          required
        >
          <option value="">약을 선택해 주세요</option>
          {meds.map(med => (
            <option key={med.med_id} value={med.med_id}>
              {med.item_name}
            </option>
          ))}
        </select>
      </div>

      <div>
        <label htmlFor="history-start">복용 시작일</label>
        <input
          id="history-start"
          type="date"
          value={startDate}
          onChange={event => setStartDate(event.target.value)}
          required
        />
      </div>

      <div>
        <label htmlFor="history-times">하루 복용 횟수 (선택)</label>
        <input
          id="history-times"
          type="number"
          min="1"
          max="24"
          step="1"
          value={timesPerDay}
          onChange={event => setTimesPerDay(event.target.value)}
          placeholder="횟수 입력"
        />
      </div>

      <div>
        <label htmlFor="history-duration">복용 기간 (일, 선택)</label>
        <input
          id="history-duration"
          type="number"
          min="1"
          step="1"
          value={durationDays}
          onChange={event => setDurationDays(event.target.value)}
          placeholder="복용 일수 입력"
        />
        <p className="muted">
          기간을 지정하지 않으면 종료일 없이 기록돼요.
        </p>
      </div>

      {error && <p role="alert">{error}</p>}
      {notice && <p role="status">{notice}</p>}

      <button
        type="submit"
        className="btn btn-primary"
        disabled={saving}
      >
        {saving ? '저장 중...' : '복용이력 저장'}
      </button>
    </form>
  )
}

export default MedHistoryForm
