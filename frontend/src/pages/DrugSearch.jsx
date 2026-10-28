import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router";

function DrugSearch() {
    const [searchParams, setSearchParams] = useSearchParams()
    const q = searchParams.get('q') ?? ''

    const [keyword, setKeyword] = useState(q)
    const [answer, setAnswer] =  useState({ q: '', total: 0, items: [], error: '' })
    const loading = q !== '' && answer.q !== q

    useEffect(() => {
        if (q === '') return
        fetch(`/api/drugs?q=${encodeURIComponent(q)}`)
            .then(async res => {
                const data = await res.json()
                if(!res.ok) throw new Error(data.detail)
                setAnswer({ q:q, total: data.total, items: data.items, error: ''})
            })
            .catch(err => setAnswer({ q: q, total: 0, items: [], error: err.message }))
    }, [q])

    const handleSearch = e =>{
        e.preventDefault()
        if (keyword.trim() === '') return
        setSearchParams({ q: keyword.trim()})
    }
    return (<>
        <h2>약 찾기</h2>
        <form onSubmit={handleSearch}>
            <input placeholder="약 이름 (예: 타이레놀)" 
            value={keyword}
            onChange={e => setKeyword(e.target.value)} />
            <button type="submit">검색</button>
        </form>

        {loading && <p>찾는 중...</p>}
        {!loading && answer.error && <p>{answer.error}</p>}
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