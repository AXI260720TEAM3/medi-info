import { useEffect, useState } from 'react'
import { Link } from 'react-router'
import ErrorMessage from '../components/ErrorMessage'
import Loading from '../components/Loading'
import MedCheck from '../components/MedCheck'
import MedProfile from '../components/MedProfile'
import MedScan from '../components/MedScan'
import MedHistory from '../components/MedHistory'
import MedReminder from '../components/MedReminder'
import PageTitle from '../components/PageTitle'

// 성분 칸 글자: 불러오는 중, 조회 실패, 정보 없음을 구분해요
function ingredientText(ingredients, itemSeq) {
  if (ingredients === null) return '불러오는 중'
  const names = ingredients[itemSeq]
  if (!names) return '확인하지 못했어요'
  if (names.length === 0) return '정보 없음'
  if (names.length === 1) return names[0]
  return `${names[0]} 외 ${names.length - 1}개`
}

function MyMeds() {
  const [meds, setMeds] = useState(null)
  const [ingredients, setIngredients] = useState(null)
  const [needLogin, setNeedLogin] = useState(false)
  const [needConsent, setNeedConsent] = useState(false)
  const [error, setError] = useState('')
  const [deleteError, setDeleteError] = useState('')
  const [checkKey, setCheckKey] = useState(0)
  const [listKey, setListKey] = useState(0)  // 사진으로 약을 넣으면 바꿔서 목록을 다시 받아요

  useEffect(() => {
    fetch('/api/my-meds')
      .then(async res => {
        if (res.status === 401) {
          setNeedLogin(true)
          return
        }
        if (res.status === 403) {
          setNeedConsent(true)
          return
        }
        if (!res.ok) throw new Error()
        setMeds(await res.json())
      })
      .catch(() => setError('내 약을 불러오지 못했어요. 잠시 후 다시 시도해 주세요.'))

    // 성분은 공공데이터를 거쳐 느릴 수 있어서 목록을 먼저 보여 주고 따로 받아요
    fetch('/api/my-meds/ingredients')
      .then(res => (res.ok ? res.json() : {}))
      .then(data => setIngredients(data))
      .catch(() => setIngredients({}))
  }, [listKey])

  const handleAdded = () => {
    setListKey(listKey + 1)
    setCheckKey(checkKey + 1)
  }

  const handleDelete = async (medId) => {
    setDeleteError('')
    try {
      const res = await fetch(`/api/my-meds/${medId}`, { method: 'DELETE' })
      if (!res.ok) throw new Error()
      setMeds(meds.filter(med => med.med_id !== medId))
      setCheckKey(checkKey + 1)
    } catch {
      setDeleteError('삭제하지 못했어요. 잠시 후 다시 시도해 주세요.')
    }
  }

  if (needLogin) {
    return <p>내 약은 로그인하면 볼 수 있어요. <Link to="/login">로그인하기</Link></p>
  }
  if (needConsent){
    return <p>내 약은 건강정보 수집에 동의하면 쓸 수 있어요. <Link to="/account">동의하러 가기</Link></p>
  }
  if (error) return <ErrorMessage message={error} />
  if (meds === null) return <Loading />

  // 화면 4단계 (11/11): 넓은 화면은 왼쪽(약봉지 사진으로 추가 → 담은 약 → 함께 먹기 결과 → 복용 이력·알림)과
  // 오른쪽(복용자 프로필) 두 칸. 좁은 화면은 왼쪽 칸이 먼저 오도록 아래로 쌓여요
  return (<>
    <PageTitle icon="pill" title="내 약">약을 담으면 함께 먹어도 되는지 짝마다 자동으로 확인해요</PageTitle>
    {deleteError && <ErrorMessage message={deleteError} />}
    <div className="mymeds-layout">
    <div className="mymeds-main">
    <MedScan onAdded={handleAdded} />
    <h2 className="section-title">담은 약 <span className="section-count">{meds.length}개</span></h2>
    {meds.length === 0 && (
      <p className="muted" style={{ margin: 0 }}>
        아직 담은 약이 없어요. 약봉지 사진이나 <Link to="/drugs">약 찾기</Link>로 담아 보세요.
      </p>
    )}
    {meds.length > 0 && (
      <div className="table-card">
        <table className="med-table">
          <thead>
            <tr>
              <th scope="col">약 이름</th>
              <th scope="col">성분</th>
              <th scope="col">추가 방법</th>
              <th scope="col"><span className="sr-only">삭제</span></th>
            </tr>
          </thead>
          <tbody>
            {meds.map(med => (
              <tr key={med.med_id}>
                <td><Link to={`/drugs/${med.item_seq}`}><strong>{med.item_name}</strong></Link></td>
                <td title={ingredients?.[med.item_seq]?.join(', ')}>{ingredientText(ingredients, med.item_seq)}</td>
                <td>{med.added_by}</td>
                <td className="med-table-action">
                  <button type="button" className="btn btn-secondary" onClick={() => handleDelete(med.med_id)}>
                    삭제
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    )}
    {meds.length >= 2 && <MedCheck key={checkKey} />}

    <MedHistory meds={meds} />
    <MedReminder />
    </div>
    <aside className="mymeds-side">
      {meds.length > 0 && <MedProfile checkKey={checkKey} onChange={() => setCheckKey(checkKey + 1)} />}
    </aside>
    </div>
  </>)
}
export default MyMeds
