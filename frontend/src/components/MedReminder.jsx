import { useEffect, useState } from 'react'
import ErrorMessage from './ErrorMessage'
import Loading from './Loading'
import MedReminderActions from './MedReminderActions'

function MedReminder() {
  const [histories, setHistories] = useState(null)
  const [reminders, setReminders] = useState(null)
  const [historyId, setHistoryId] = useState('')
  const [remindTime, setRemindTime] = useState('')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')

  const loadReminders = async () => {
    const res = await fetch('/api/med-reminders')
    if (!res.ok) {
      throw new Error('복약 알림 목록을 불러오지 못했어요.')
    }
    setReminders(await res.json())
  }

  useEffect(() => {
    const load = async () => {
      const historyRes = await fetch('/api/med-history')

      if (!historyRes.ok) {
        throw new Error('복용이력을 불러오지 못했어요.')
      }

      setHistories(await historyRes.json())
      await loadReminders()
    }

    load().catch(err => setError(err.message))
  }, [])

  const handleSave = async (e) => {
    e.preventDefault()
    setError('')
    setMessage('')
    setSaving(true)

    try {
      const res = await fetch('/api/med-reminders', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          history_id: Number(historyId),
          remind_time: remindTime,
        }),
      })

      if (!res.ok) {
        const data = await res.json().catch(() => ({}))
        throw new Error(
          typeof data.detail === 'string'
            ? data.detail
            : '알림 등록에 실패했어요.'
        )
      }

      await loadReminders()
      setHistoryId('')
      setRemindTime('')
      setMessage('알림 시간을 저장했어요.')
    } catch (err) {
      setError(err.message)
    } finally {
      setSaving(false)
    }
  }

  if (histories === null || reminders === null) {
    if (error) return <ErrorMessage message={error} />
    return <Loading />
  }

  const activeHistories = histories.filter(
    history => history.stopped_at === null
  )

  return (
    <section>
      <h2>복약 알림</h2>
      <p className="muted">
        복용 중인 약의 알림 시간을 설정할 수 있어요.
      </p>

      <h3>알림 시간 등록</h3>

      {activeHistories.length === 0 ? (
        <p className="muted">
          먼저 복용 중인 약을 기록해 주세요.
        </p>
      ) : (
        <form onSubmit={handleSave}>
          <div>
            <label htmlFor="reminder-history">
              약 선택
            </label>
            <select
              id="reminder-history"
              value={historyId}
              onChange={e => setHistoryId(e.target.value)}
              required
            >
              <option value="">약을 선택해 주세요</option>
              {activeHistories.map(history => (
                <option
                  key={history.history_id}
                  value={history.history_id}
                >
                  {history.item_name} ({history.start_date} 시작)
                </option>
              ))}
            </select>
          </div>

          <div>
            <label htmlFor="reminder-time">
              알림 시간
            </label>
            <input
              id="reminder-time"
              type="time"
              value={remindTime}
              onChange={e => setRemindTime(e.target.value)}
              required
            />
          </div>

          <button
            type="submit"
            className="btn btn-primary"
            disabled={saving}
          >
            {saving ? '저장 중...' : '알림 시간 저장'}
          </button>
        </form>
      )}

      {message && <p role="status">{message}</p>}
      {error && <ErrorMessage message={error} />}

      <h3>등록된 알림</h3>

      {reminders.length === 0 ? (
        <p className="muted">아직 등록된 알림이 없어요.</p>
      ) : (
        <div className="table-card">
          <table className="med-table">
            <thead>
              <tr>
                <th>약 이름</th>
                <th>알림 시간</th>
                <th>상태</th>
                <th>관리</th>
              </tr>
            </thead>
            <tbody>
              {reminders.map(reminder => (
                <tr key={reminder.reminder_id}>
                  <td>{reminder.item_name}</td>
                  <td>{reminder.remind_time.slice(0, 5)}</td>
                  <td>
                    {reminder.stopped_at
                      ? '복용 중단'
                      : reminder.is_enabled
                        ? '설정 켜짐'
                        : '설정 꺼짐'}
                  </td>
                  <td>
                 <MedReminderActions
                reminder={reminder}
                onSaved={loadReminders}
  />
</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <p className="muted">
        현재는 알림 시간 저장 기능이며,
        실제 알림 발송은 아직 구현 전이에요.
      </p>
    </section>
  )
}

export default MedReminder
