import { useEffect, useState } from 'react'
import { Link } from 'react-router'
import ErrorMessage from '../components/ErrorMessage'
import Loading from '../components/Loading'

function MyMeds() {
  const [meds, setMeds] = useState(null)
  const [needLogin, setNeedLogin] = useState(false)
  const [error, setError] = useState('')
  const [deleteError, setDeleteError] = useState('')

  useEffect(() => {
    fetch('/api/my-meds')
      .then(async res => {
        if (res.status === 401) {
          setNeedLogin(true)
          return
        }
        if (!res.ok) throw new Error()
        setMeds(await res.json())
      })
      .catch(() => setError('내 약을 불러오지 못했어요. 잠시 후 다시 시도해 주세요.'))
  }, [])

  const handleDelete = async (medId) => {
    setDeleteError('')
    try {
      const res = await fetch(`/api/my-meds/${medId}`, { method: 'DELETE' })
      if (!res.ok) throw new Error()
      setMeds(meds.filter(med => med.med_id !== medId))
    } catch {
      setDeleteError('삭제하지 못했어요. 잠시 후 다시 시도해 주세요.')
    }
  }

  if (needLogin) {
    return <p>내 약은 로그인하면 볼 수 있어요. <Link to="/login">로그인하기</Link></p>
  }
  if (error) return <ErrorMessage message={error} />
  if (meds === null) return <Loading />

  return (<>
    <h1 className="title">내 약</h1>
    {deleteError && <ErrorMessage message={deleteError} />}
    {meds.length === 0 && <p className="muted">등록한 약이 없어요.</p>}
    {meds.map(med => (
      <div key={med.med_id} className="card">
        <p>{med.item_name}</p>
        <button type="button" className="btn btn-secondary" onClick={() => handleDelete(med.med_id)}>
          삭제
        </button>
      </div>
    ))}
  </>)
}
export default MyMeds
