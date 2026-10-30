import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router";

function DrugSearch() {
    const [searchParams, setSearchParams] = useSearchParams()
    const q = searchParams.get('q') ?? ''

    const [keyword, setKeyword] = useState(q)
    const [answer, setAnswer] =  useState({ q: '', total: 0, items: [], error: '', parsed:null })
    const loading = q !== '' && answer.q !== q
    const found = answer.parsed && (answer.parsed.drug_name ?? answer.parsed.symptom)

    useEffect(() => {
        if (q === '') return
        fetch(`/api/drugs/smart?text=${encodeURIComponent(q)}`)
            .then(async res => {
                const data = await res.json()
                if(!res.ok) throw new Error(data.detail)
                setAnswer({ q:q, total: data.total, items: data.items, error: '', parsed: data.parsed })
            })
            .catch(err => setAnswer({ q: q, total: 0, items: [], error: err.message, parsed: null }))
    }, [q])

    const handleSearch = e =>{
        e.preventDefault()
        if (keyword.trim() === '') return
        setSearchParams({ q: keyword.trim()})
    }
    return (<>
        <h2>약 찾기</h2>
        <form onSubmit={handleSearch}>
            <input placeholder="약 이름이나 증상을 말해 보세요 (예: 머리가 지끈거려요)" 
            value={keyword}
            onChange={e => setKeyword(e.target.value)} />
            <button type="submit">검색</button>
        </form>

        {loading && <p>찾는 중...</p>}
        {!loading && answer.error && <p>{answer.error}</p>}
        {!loading && answer.parsed && (found
            ? <p>🤖 '{found}'(으)로 찾았어요</p>
            : <p>🤖 약 이름이나 증상을 알아듣지 못했어요. 다르게 말해 볼까요?</p>)}
        {!loading && answer.q !== '' && !answer.error && <p>{answer.total}건</p>}

        <ul>
            {!loading && answer.items.map(drug =>(
                <li key={drug.item_seq}>
                    <Link to={`/drugs/${drug.item_seq}`}>{drug.item_name}</Link>
                    <span> · {drug.entp_name}</span>
                </li>
            ))}
        </ul>
    </>)
}
export default DrugSearch