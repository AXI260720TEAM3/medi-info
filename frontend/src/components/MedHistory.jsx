
import { useEffect, useState } from 'react'
import ErrorMessage from './ErrorMessage'
import Loading from './Loading'
import MedHistoryForm from './MedHistoryForm'
import MedHistoryActions from './MedHistoryActions'

function MedHistory({ meds }) {
  const [histories, setHistories] = useState(null)
  const [error, setError] = useState('')

  const loadHistories = async () => {
    const res = await fetch('/api/med-history')
    if (!res.ok) {
      throw new Error('복용이력을 불러오지 못했어요.')
    }
    const data = await res.json()
    setHistories(data)
  }

  useEffect(() => {
    loadHistories().catch(err => setError(err.message))
  }, [])

  if (error && histories === null) {
    return <ErrorMessage message={error} />
  }

  if (histories === null) {
    return <Loading />
  }

  return (
    <section>
      <h2>복용이력</h2>
      <p className="muted">
        복용 시작일과 중단일을 직접 기록할 수 있어요.
      </p>

      <MedHistoryForm
  meds={meds}
  onSaved={() => {
    setError('')
    loadHistories().catch(err => setError(err.message))
  }}
/>

{error && <ErrorMessage message={error} />}

      {histories.length === 0 ? (
        <p className="muted">아직 등록한 복용이력이 없어요.</p>
      ) : (
        <div className="table-card">
          <table className="med-table">
            <thead>
              <tr>
                <th>약 이름</th>
                <th>시작일</th>
                <th>하루 횟수</th>
                <th>중단일</th>
                <th>관리</th>
              </tr>
            </thead>
            <tbody>
              {histories.map(history => (
                <tr key={history.history_id}>
                  <td>{history.item_name}</td>
                  <td>{history.start_date}</td>
                  <td>{history.times_per_day ?? '미입력'}</td>
                  <td>{history.stopped_at ?? '미기록'}</td>
                  <td>
                 <MedHistoryActions
                 history={history}
                 onSaved={() => {
                setError('')
                loadHistories().catch(err => setError(err.message))
    }}
  />
</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  )
}

export default MedHistory
