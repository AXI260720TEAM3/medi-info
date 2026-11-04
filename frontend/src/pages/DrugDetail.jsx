import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router";

const SECTIONS = [
  ['efcy', '이 약의 효능은 무엇입니까?'],
  ['use_method', '이 약은 어떻게 사용합니까?'],
  ['atpn_warn', '이 약을 사용하기 전에 반드시 알아야 할 내용은 무엇입니까?'],
  ['atpn', '이 약의 사용상 주의사항은 무엇입니까?'],
  ['intrc', '이 약을 사용하는 동안 주의해야 할 약 또는 음식은 무엇입니까?'],
  ['se', '이 약은 어떤 이상반응이 나타날 수 있습니까?'],
  ['deposit', '이 약은 어떻게 보관해야 합니까?'],
]

function DrugDetail() {
    const {itemSeq} = useParams()
    const navigate = useNavigate()
    const [answer,setAnswer] = useState({ seq: '', drug: null, error: ''})
    const [message, setMessage] = useState('')
    const loading = answer.seq !== itemSeq

    useEffect(() => {
        fetch(`/api/drugs/${itemSeq}`)
        .then(async res => {
            const data = await res.json()
            if(!res.ok) throw new Error(data.detail)
            setAnswer({seq: itemSeq, drug: data, error: ''})
        })
        .catch(err => setAnswer({ seq: itemSeq, drug: null, error: err.message }))
    }, [itemSeq])

    if (loading) return <p>불러오는 중...</p>
    if (answer.error) return <p>{answer.error} <Link to="/drugs">검색으로</Link></p>

    const drug = answer.drug
    const handleAdd = async () => {
        const res = await fetch('/api/my-meds', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ item_seq: itemSeq, item_name: drug.item_name }),
        })
        if (res.status === 201) setMessage('내 약에 등록했어요.')
        else if (res.status === 409) setMessage('이미 등록한 약이에요.')
        else if (res.status === 401) setMessage('로그인하면 등록할 수 있어요.')
        else if (res.status === 403) setMessage('건강정보 수집에 동의하면 등록할 수 있어요. 내 정보 화면에서 동의할 수 있어요.')
        else setMessage('등록하지 못했어요. 잠시 후 다시 시도해 주세요.')
    }
    return (<>
        <button onClick={() => navigate(-1)}>← 목록으로</button>
        <h2>{drug.item_name}</h2>
        <p>{drug.entp_name}</p>
        <button type="button" className="btn btn-primary" onClick={handleAdd}>내 약에 등록</button>
        {message && <p className="muted">{message}</p>}
        {drug.item_image && <img src={drug.item_image} alt={drug.item_name} width="200" /> }

        {SECTIONS.map(([key, title]) => (
            <section key={key}>
                <h3>{title}</h3>
                <p style={{ whiteSpace: 'pre-line' }}>{drug[key] || '정보 없음'}</p>
            </section>
        ))}
    
        <p>출처: 식품의약품안전처 의약품개요정보(e약은요) · 수정일 {drug.update_de}</p>
    </>)
}
export default DrugDetail
