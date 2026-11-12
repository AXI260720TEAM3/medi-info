
import { useEffect, useState } from 'react'
import ErrorMessage from './ErrorMessage'
import Loading from './Loading'
import MedHistoryForm from './MedHistoryForm'
import MedHistoryActions from './MedHistoryActions'

function MedHistory({ meds, onChanged }) {
  const [histories, setHistories] = useState(null)
  const [error, setError] = useState('')
  const [page, setPage] = useState(1)

  const loadHistories = async () => {
    const res = await fetch('/api/med-history')

    if (!res.ok) {
      throw new Error('복용이력을 불러오지 못했어요.')
    }

    const data = await res.json()
    setHistories(data)
  }

  const handleSaved = () => {
    setError('')
    loadHistories().catch(err => setError(err.message))
    onChanged?.()
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

  const pageSize = 6
  const totalPages = Math.ceil(histories.length / pageSize)
  const currentPage = Math.min(page, Math.max(1, totalPages))
  const visibleHistories = histories.slice(
    (currentPage - 1) * pageSize,
    currentPage * pageSize
  )

  return (
    <section className="card med-panel">
      <div>
        <h2 className="panel-title">복용이력</h2>
        <p className="muted" style={{ margin: '4px 0 0' }}>
          복용 시작일과 중단일을 직접 기록할 수 있어요.
        </p>
      </div>

      <MedHistoryForm
        meds={meds}
        onSaved={handleSaved}
      />

      {error && <ErrorMessage message={error} />}

      {histories.length === 0 ? (
        <p className="muted" style={{ margin: 0 }}>
          아직 등록한 복용이력이 없어요.
        </p>
      ) : (
        <div className="table-card">
          <table className="med-table">
            <thead>
              <tr>
                <th>약 이름</th>
                <th>시작일</th>
                <th>하루 횟수</th>
                <th>복용 기간</th>
                <th>중단일</th>
                <th>관리</th>
              </tr>
            </thead>
            <tbody>
              {visibleHistories.map(history => (
                <tr key={history.history_id}>
                  <td>{history.item_name}</td>
                  <td>{history.start_date}</td>
                  <td>{history.times_per_day ?? '미입력'}</td>
                  <td>
                    {history.duration_days == null
                      ? '기간 지정 없음'
                      : `${history.duration_days}일`}
                  </td>
                  <td>{history.stopped_at ?? '미기록'}</td>
                  <td>
                    <MedHistoryActions
                      history={history}
                      onSaved={handleSaved}
                    />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          {totalPages > 1 && (
            <div
              style={{
                display: 'flex',
                justifyContent: 'center',
                alignItems: 'center',
                gap: '6px',
                padding: '16px',
                flexWrap: 'wrap',
              }}
            >
              <button
                type="button"
                className="btn btn-secondary btn-small"
                disabled={currentPage === 1}
                onClick={() => setPage(currentPage - 1)}
                aria-label="이전 페이지"
              >
                〈
              </button>

              {Array.from(
                { length: totalPages },
                (_, i) => i + 1
              ).map(number => (
                <button
                  key={number}
                  type="button"
                  className={`btn btn-small ${
                    currentPage === number
                      ? 'btn-primary'
                      : 'btn-secondary'
                  }`}
                  onClick={() => setPage(number)}
                  aria-current={
                    currentPage === number
                      ? 'page'
                      : undefined
                  }
                >
                  {number}
                </button>
              ))}

              <button
                type="button"
                className="btn btn-secondary btn-small"
                disabled={currentPage === totalPages}
                onClick={() => setPage(currentPage + 1)}
                aria-label="다음 페이지"
              >
                〉
              </button>
            </div>
          )}
        </div>
      )}
    </section>
  )
}

export default MedHistory
