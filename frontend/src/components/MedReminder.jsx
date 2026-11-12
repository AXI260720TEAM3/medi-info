
import { useEffect, useState } from 'react'
import ErrorMessage from './ErrorMessage'
import Loading from './Loading'
import MedReminderActions from './MedReminderActions'
import {
  ensurePushSubscription,
  disableDevicePush,
  isPushDisabled,
} from '../utils/pushSubscription'

const ALARM_LABELS = [
  '아침',
  '점심',
  '저녁',
  '취침 전',
  '식전',
  '식후',
]

function formatAlarmTime(time) {
  const [hour, minute] = time.slice(0, 5).split(':').map(Number)
  const period = hour < 12 ? '오전' : '오후'
  const displayHour = hour % 12 || 12

  return `${period} ${displayHour}:${String(minute).padStart(2, '0')}`
}

function MedReminder() {
  const [histories, setHistories] = useState(null)
  const [reminders, setReminders] = useState(null)
  const [historyId, setHistoryId] = useState('')
  const [alarmLabel, setAlarmLabel] = useState('')
  const [remindTime, setRemindTime] = useState('')
  const [saving, setSaving] = useState(false)
  const [devicePushDisabled, setDevicePushDisabled] = useState(isPushDisabled)
  const [deviceBusy, setDeviceBusy] = useState(false)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')

  const loadReminders = async () => {
    const res = await fetch('/api/med-reminders')

    if (!res.ok) {
      throw new Error('복약 알람 목록을 불러오지 못했어요.')
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

  const handleSave = async (event) => {
    event.preventDefault()
    setError('')
    setMessage('')
    setSaving(true)

    try {
      await ensurePushSubscription()

      const res = await fetch('/api/med-reminders', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          history_id: Number(historyId),
          alarm_label: alarmLabel,
          remind_time: remindTime,
        }),
      })

      if (!res.ok) {
        const data = await res.json().catch(() => ({}))
        throw new Error(
          typeof data.detail === 'string'
            ? data.detail
            : '복약 알람 저장에 실패했어요.'
        )
      }

      await loadReminders()

      setAlarmLabel('')
      setRemindTime('')
      setMessage('복약 알람을 저장했어요.')
    } catch (err) {
      setError(err.message || '저장 중 오류가 발생했어요.')
    } finally {
      setSaving(false)
    }
  }

  const handleDevicePushToggle = async () => {
    setDeviceBusy(true)
    setError('')
    setMessage('')

    try {
      if (devicePushDisabled) {
        await ensurePushSubscription(true)
        setDevicePushDisabled(false)
        setMessage('이 기기 알림을 켰어요.')
      } else {
        await disableDevicePush()
        setDevicePushDisabled(true)
        setMessage('이 기기 알림을 껐어요. 등록된 알람은 유지돼요.')
      }
    } catch (err) {
      setError(err.message || '기기 알림 설정에 실패했어요.')
    } finally {
      setDeviceBusy(false)
    }
  }

  if (histories === null || reminders === null) {
    if (error) return <ErrorMessage message={error} />
    return <Loading />
  }

  const activeHistories = histories.filter(
    history => history.stopped_at === null
  )

  const groupedReminders = reminders.reduce((groups, reminder) => {
    let group = groups.find(
      item => item.history_id === reminder.history_id
    )

    if (!group) {
      group = {
        history_id: reminder.history_id,
        item_name: reminder.item_name,
        reminders: [],
      }
      groups.push(group)
    }

    group.reminders.push(reminder)
    return groups
  }, [])

  const fieldStyle = {
    display: 'grid',
    gap: '6px',
    minWidth: 0,
    alignContent: 'start',
  }

  return (
    <section className="card med-panel">
      <div>
        <h2 className="panel-title">복약 알람</h2>
        <p className="muted" style={{ margin: '4px 0 0' }}>
          복용 중인 약의 알림 시간을 설정할 수 있어요.
        </p>
      </div>

      {activeHistories.length === 0 ? (
        <>
          <h3 className="panel-subtitle">알림 시간 등록</h3>
          <p className="muted" style={{ margin: 0 }}>
            먼저 복용 중인 약을 기록해 주세요.
          </p>
        </>
      ) : (
        <form
          onSubmit={handleSave}
          className="med-form"
          style={{
            display: 'grid',
            gridTemplateColumns:
              'repeat(auto-fit, minmax(min(100%, 180px), 1fr))',
            gap: '12px',
            alignItems: 'end',
            width: '100%',
          }}
        >
          <h3
            className="panel-subtitle"
            style={{ gridColumn: '1 / -1', margin: 0 }}
          >
            알림 시간 등록
          </h3>

          <div className="med-field" style={fieldStyle}>
            <label htmlFor="reminder-history">
              약 선택
            </label>
            <select
              id="reminder-history"
              className="input"
              style={{ width: '100%', minWidth: 0 }}
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
                  {history.item_name}
                </option>
              ))}
            </select>
          </div>

          <div className="med-field" style={fieldStyle}>
            <label htmlFor="reminder-label">
              복용 시간대
            </label>
            <select
              id="reminder-label"
              className="input"
              style={{ width: '100%', minWidth: 0 }}
              value={alarmLabel}
              onChange={e => setAlarmLabel(e.target.value)}
              required
            >
              <option value="">선택해 주세요</option>
              {ALARM_LABELS.map(label => (
                <option key={label} value={label}>
                  {label}
                </option>
              ))}
            </select>
          </div>

          <div className="med-field" style={fieldStyle}>
            <label htmlFor="reminder-time">
              알람 시간
            </label>
            <input
              id="reminder-time"
              className="input"
              style={{ width: '100%', minWidth: 0 }}
              type="time"
              value={remindTime}
              onChange={e => setRemindTime(e.target.value)}
              required
            />
          </div>

          <div
            style={{
              gridColumn: '1 / -1',
              display: 'flex',
              justifyContent: 'flex-end',
            }}
          >
            <button
              type="submit"
              className="btn btn-primary"
              disabled={saving}
            >
              {saving ? '저장 중...' : '복약 알람 저장'}
            </button>
          </div>
        </form>
      )}

      {message && (
        <p role="status" className="form-notice">
          {message}
        </p>
      )}

      {error && <ErrorMessage message={error} />}

      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: '12px',
          flexWrap: 'wrap',
        }}
      >
        <h3 className="panel-subtitle">등록된 알람</h3>

        <button
          type="button"
          className="btn btn-secondary"
          onClick={handleDevicePushToggle}
          disabled={deviceBusy || saving}
        >
          {deviceBusy
            ? '처리 중...'
            : devicePushDisabled
              ? '이 기기 알림 켜기'
              : '이 기기 알림 끄기'}
        </button>
      </div>

      {groupedReminders.length === 0 ? (
        <p className="muted" style={{ margin: 0 }}>
          아직 등록된 알람이 없어요.
        </p>
      ) : (
        <div className="table-card">
          {groupedReminders.map(group => (
            <div
              key={group.history_id}
              style={{
                padding: '12px',
                borderBottom: '1px solid #ddd',
              }}
            >
              <strong>{group.item_name}</strong>

              {group.reminders.map(reminder => (
                <div
                  key={reminder.reminder_id}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '12px',
                    flexWrap: 'wrap',
                    marginTop: '8px',
                  }}
                >
                  <span>
                    {reminder.alarm_label ?? '시간대 미설정'}
                    {' · '}
                    {formatAlarmTime(reminder.remind_time)}
                  </span>

                  <span>
                    {reminder.stopped_at
                      ? '복용 중단'
                      : reminder.is_enabled
                        ? '켜짐'
                        : '꺼짐'}
                  </span>

                  <MedReminderActions
                    reminder={reminder}
                    onSaved={loadReminders}
                  />
                </div>
              ))}
            </div>
          ))}
        </div>
      )}
    </section>
  )
}

export default MedReminder
