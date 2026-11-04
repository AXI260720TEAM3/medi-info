import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router";

const PAGE_SIZE = 10
const PAGE_LINKS = 5 // 쪽 번호를 한 번에 몇 개 보여 줄지

function DrugSearch() {
    const [searchParams, setSearchParams] = useSearchParams()
    const q = searchParams.get('q') ?? ''
    const page = Math.max(1, Number(searchParams.get('page')) || 1)
    const key = `${q}|${page}` // 어떤 검색어의 몇 쪽 결과인지

    const [keyword, setKeyword] = useState(q)
    const [answer, setAnswer] =  useState({ key: '', total: 0, items: [], error: '', parsed:null })
    const loading = q !== '' && answer.key !== key
    const found = answer.parsed && (answer.parsed.drug_name ?? answer.parsed.symptom)
    const totalPages = Math.ceil(answer.total / PAGE_SIZE)

    useEffect(() => {
        if (q === '') return
        fetch(`/api/drugs/smart?text=${encodeURIComponent(q)}&page=${page}`)
            .then(async res => {
                const data = await res.json()
                if(!res.ok) throw new Error(data.detail)
                setAnswer({ key: key, total: data.total, items: data.items, error: '', parsed: data.parsed })
            })
            .catch(err => setAnswer({ key: key, total: 0, items: [], error: err.message, parsed: null }))
    }, [q, page, key])

    const handleSearch = e =>{
        e.preventDefault()
        if (keyword.trim() === '') return
        setSearchParams({ q: keyword.trim()}) // 새 검색은 1쪽부터
    }

    const goPage = p => {
        setSearchParams({ q:q, page: String(p) })
        window.scrollTo(0,0)
    }

    // 지금 쪽이 가운데 오도록 쪽 번호 5개를 고른다
    const first = Math.max(1,Math.min(page - Math.floor(PAGE_LINKS / 2), totalPages - PAGE_LINKS + 1))
    const pages = []
    for (let p = first; p <= Math.min(totalPages, first + PAGE_LINKS -1); p++) pages.push(p)

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
        {!loading && answer.key !== '' && !answer.error && (
            <p>{answer.total}건{totalPages > 1 && ` · ${page} / ${totalPages}쪽`}</p>
        )}
        {!loading && found && !answer.error && answer.total === 0 && (
            <p>식약처 e약은요에 등록된 일반의약품만 검색됩니다. 약사와 상담해 보세요.</p>
        )}

        <ul>
            {!loading && answer.items.map(drug =>(
                <li key={drug.item_seq}>
                    <Link to={`/drugs/${drug.item_seq}`}>{drug.item_name}</Link>
                    <span> · {drug.entp_name}</span>
                </li>
            ))}
        </ul>

        {!loading && totalPages > 1 && (
            <nav style={{ display: 'flex', flexWrap: 'wrap', gap: 4, alignItems: 'center' }} aria-label="검색 결과 쪽">
                <button type="button" className="btn btn-secondary" onClick={() => goPage(page - 1)} disabled={page <= 1}>이전</button>
                {pages.map(p => (
                    <button key={p} type="button" onClick={() => goPage(p)} disabled={p === page}
                        className={p === page ? 'btn btn-primary' : 'btn btn-secondary'}
                        aria-current={p === page ? 'page' : undefined}>{p}</button>
                ))}
                <button type="button" className="btn btn-secondary" onClick={() => goPage(page + 1)} disabled={page >= totalPages}>다음</button>
            </nav>
        )}
    </>)
}
export default DrugSearch