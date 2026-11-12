
import { useState } from 'react'

function MedHistoryActions({ history, onSaved }) {
  const [mode, setMode] = useState('')
  const [startDate, setStartDate] = useState(history.start_date)
  const [times, setTimes] = useState(
    history.times_per_day?.toString() ?? ''
  )
  const [durationDays, setDurationDays] = useState(
  history.duration_days?.toString() ?? ''
)
  const [stopDate, setStopDate] = useState('')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  const openEdit = () => {
    setStartDate(history.start_date)
    setTimes(history.times_per_day?.toString() ?? '')
    setDurationDays(history.duration_days?.toString() ?? '')
    setError('')
    setMode('edit')
  }

  const openStop = () => {
    setStopDate('')
    setError('')
    setMode('stop')
  }

  const cancel = () => {
    setMode('')
    setError('')
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setSaving(true)

    const isEdit = mode === 'edit'

    const url = isEdit
      ? `/api/med-history/${history.history_id}`
      : `/api/med-history/${history.history_id}/stop`

    const body = isEdit
      ? {
          start_date: startDate,
          times_per_day: times === '' ? null : Number(times),
          duration_days: durationDays === '' ? null : Number(durationDays),
        }
      : {
          stopped_at: stopDate,
        }

    try {
      const res = await fetch(url, {
        method: isEdit ? 'PUT' : 'PATCH',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(body),
      })

      if (!res.ok) {
        const data = await res.json().catch(() => ({}))
        throw new Error(
          typeof data.detail === 'string'
            ? data.detail
            : '복용이력 변경에 실패했어요.'
        )
      }

      setMode('')
      onSaved()
    } catch (err) {
      setError(err.message)
    } finally {
      setSaving(false)
    }
  }

  return (
    <div>
      <div className="med-actions">
        <button type="button" className="btn btn-secondary btn-small" onClick={openEdit}>
          수정
        </button>

        {!history.stopped_at && (
          <button type="button" className="btn btn-secondary btn-small" onClick={openStop}>
            복용 중단
          </button>
        )}
      </div>

      {mode && (
        <form onSubmit={handleSubmit} className="med-inline-form">
          {mode === 'edit' ? (
            <>
              <label>
                복용 시작일
                <input
                  type="date"
                  className="input"
                  value={startDate}
                  onChange={e => setStartDate(e.target.value)}
                  required
                />
              </label>

              <label>
                하루 복용 횟수 (선택)
                <input
                  type="number"
                  className="input"
                  min="1"
                  max="24"
                  value={times}
                  onChange={e => setTimes(e.target.value)}
                />
              </label>

              <label>
                복용 기간 (일, 선택)
                <input
                  type="number"
                  min="1"
                  step="1"
                  value={durationDays}
                  onChange={e => setDurationDays(e.target.value)}
                  placeholder="복용 일수 입력"
                />
              </label>
            </>
          ) : (
            <label>
              복용 중단일
              <input
                type="date"
                className="input"
                min={history.start_date}
                value={stopDate}
                onChange={e => setStopDate(e.target.value)}
                required
              />
            </label>
          )}

          <button type="submit" className="btn btn-primary btn-small" disabled={saving}>
            {saving ? '저장 중...' : '저장'}
          </button>

          <button
            type="button"
            className="btn btn-secondary btn-small"
            onClick={cancel}
            disabled={saving}
          >
            취소
          </button>
        </form>
      )}

      {error && <p role="alert" className="form-error">{error}</p>}
    </div>
  )
}

export default MedHistoryActions
