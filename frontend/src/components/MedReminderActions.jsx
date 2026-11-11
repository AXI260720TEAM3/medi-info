
import { useState } from 'react'

function MedReminderActions({ reminder, onSaved }) {
  const [editing, setEditing] = useState(false)
  const [time, setTime] = useState(
    reminder.remind_time.slice(0, 5)
  )
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  const isStopped = reminder.stopped_at !== null

  const sendRequest = async (method, body) => {
    const res = await fetch(
      `/api/med-reminders/${reminder.reminder_id}`,
      {
        method,
        headers: {
          'Content-Type': 'application/json',
        },
        ...(body ? { body: JSON.stringify(body) } : {}),
      }
    )

    if (!res.ok) {
      const data = await res.json().catch(() => ({}))
      throw new Error(
        typeof data.detail === 'string'
          ? data.detail
          : '알림 변경에 실패했어요.'
      )
    }

    await onSaved()
  }

  const saveTime = async (e) => {
    e.preventDefault()
    setError('')
    setSaving(true)

    try {
      await sendRequest('PUT', {
        remind_time: time,
        is_enabled: reminder.is_enabled,
      })
      setEditing(false)
    } catch (err) {
      setError(err.message)
    } finally {
      setSaving(false)
    }
  }

  const toggleReminder = async () => {
    setError('')
    setSaving(true)

    try {
      await sendRequest('PUT', {
        remind_time: reminder.remind_time,
        is_enabled: !reminder.is_enabled,
      })
    } catch (err) {
      setError(err.message)
    } finally {
      setSaving(false)
    }
  }

  const deleteReminder = async () => {
    if (!window.confirm('이 알림 시간을 삭제할까요?')) {
      return
    }

    setError('')
    setSaving(true)

    try {
      await sendRequest('DELETE')
    } catch (err) {
      setError(err.message)
    } finally {
      setSaving(false)
    }
  }

  return (
    <div>
      <div className="med-actions">
      <button
        type="button"
        className="btn btn-secondary btn-small"
        onClick={() => {
          setTime(reminder.remind_time.slice(0, 5))
          setError('')
          setEditing(true)
        }}
        disabled={saving || isStopped}
      >
        수정
      </button>

      <button
        type="button"
        className="btn btn-secondary btn-small"
        onClick={toggleReminder}
        disabled={saving || isStopped}
      >
        {reminder.is_enabled ? '끄기' : '켜기'}
      </button>

      <button
        type="button"
        className="btn btn-secondary btn-small"
        onClick={deleteReminder}
        disabled={saving}
      >
        삭제
      </button>
      </div>

      {editing && (
        <form onSubmit={saveTime} className="med-inline-form">
          <label>
            변경할 시간
            <input
              type="time"
              className="input"
              value={time}
              onChange={e => setTime(e.target.value)}
              required
            />
          </label>

          <button type="submit" className="btn btn-primary btn-small" disabled={saving}>
            저장
          </button>

          <button
            type="button"
            className="btn btn-secondary btn-small"
            disabled={saving}
            onClick={() => setEditing(false)}
          >
            취소
          </button>
        </form>
      )}

      {error && <p role="alert" className="form-error">{error}</p>}
    </div>
  )
}

export default MedReminderActions
