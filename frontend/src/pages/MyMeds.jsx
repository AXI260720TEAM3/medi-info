import { useEffect, useState } from 'react'
import { Link } from 'react-router'

function MyMeds() {
  const [meds, setMeds] = useState([])
  const [needLogin, setNeedLogin] = useState(false)

  useEffect(() => {
    fetch('/api/my-meds')
      .then(res => {
        if (res.status === 401) setNeedLogin(true)
        return res.ok ? res.json() : []
      })
      .then(data => setMeds(data))
  }, [])

  const handleDelete = async (medId) => {
    const res = await fetch(`/api/my-meds/${medId}`, { method: 'DELETE' })
    if (res.ok) {
      setMeds(meds.filter(med => med.med_id !== medId))
    }
  }

  if (needLogin) {
    return <p>내 약은 로그인하면 볼 수 있어요. <Link to="/login">로그인하기</Link></p>
  }

  return (<>
    <h1 className="title">내 약</h1>
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
