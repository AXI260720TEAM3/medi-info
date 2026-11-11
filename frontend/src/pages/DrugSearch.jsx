import { useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router'
import Loading from '../components/Loading'
import ErrorMessage from '../components/ErrorMessage'
import AlertBox from '../components/AlertBox'
import DrugImage from '../components/DrugImage'
import Badge from '../components/Badge'
import DurBadges from '../components/DurBadges'
import PageTitle from '../components/PageTitle'

const PAGE_SIZE = 10
const PAGE_LINKS = 5   // 쪽 번호를 한 번에 몇 개 보여 줄지
const EXAMPLES = ['타이레놀', '머리가 지끈거려요', '콧물이 나요']

const COLUMN = { display: 'flex', flexDirection: 'column', gap: 16 }
const PAGE_BTN = { minWidth: 44, padding: '0 12px' }

function DrugSearch() {
  const [searchParams, setSearchParams] = useSearchParams()
  const q = searchParams.get('q') ?? ''
  const page = Math.max(1, Number(searchParams.get('page')) || 1)
  const key = `${q}|${page}`   // 어떤 검색어의 몇 쪽 결과인지

  const [keyword, setKeyword] = useState(q)
  const [answer, setAnswer] = useState({ key: '', total: 0, items: [], error: '', parsed: null })
  const [retry, setRetry] = useState(0)
  const loading = q !== '' && answer.key !== key
  const totalPages = Math.ceil(answer.total / PAGE_SIZE)

  // AI가 알아들은 것: 약 이름이면 이름 검색, 증상이면 효능 검색
  // 서버와 같은 순서: 약 이름 → 성분 → 회사 → 증상 (A-1, 11/10)
  const drugName = answer.parsed?.drug_name ?? null
  const ingredient = drugName ? null : (answer.parsed?.ingredient ?? null)
  const company = drugName || ingredient ? null : (answer.parsed?.company ?? null)
  const symptom = drugName || ingredient || company ? null : (answer.parsed?.symptom ?? null)
  const ingredientEn = answer.parsed?.ingredient_en ?? null
  const ingredientAll = answer.parsed?.ingredient_all ?? 0   // 허가정보 전체 건수 (앞 100건만 받아요)
  const found = drugName ?? ingredient ?? company ?? symptom

  useEffect(() => {
    if (q === '') return
    fetch(`/api/drugs/smart?text=${encodeURIComponent(q)}&page=${page}`)
      .then(async res => {
        const data = await res.json().catch(() => ({}))
        if (!res.ok) throw new Error(typeof data.detail === 'string' ? data.detail : '검색하지 못했어요. 잠시 후 다시 시도해 주세요.')
        setAnswer({ key: key, total: data.total, items: data.items, error: '', parsed: data.parsed })
      })
      .catch(err => setAnswer({ key: key, total: 0, items: [], error: err.message, parsed: null }))
  }, [q, page, key, retry])

  const search = text => {
    if (text.trim() === '') return
    setKeyword(text.trim())
    setSearchParams({ q: text.trim() })   // 새 검색은 1쪽부터
  }

  const handleSearch = e => {
    e.preventDefault()
    search(keyword)
  }

  const goPage = p => {
    setSearchParams({ q: q, page: String(p) })
    window.scrollTo(0, 0)
  }

  // 지금 쪽이 가운데 오도록 쪽 번호 5개를 고른다
  const first = Math.max(1, Math.min(page - Math.floor(PAGE_LINKS / 2), totalPages - PAGE_LINKS + 1))
  const pages = []
  for (let p = first; p <= Math.min(totalPages, first + PAGE_LINKS - 1); p++) pages.push(p)

  const showResult = !loading && q !== '' && !answer.error

  return (
    <div style={COLUMN}>
      <PageTitle icon="search" title="약 찾기">약 이름이나 증상으로 찾아보세요</PageTitle>

      <form className="card search-form" onSubmit={handleSearch}>
        <label htmlFor="drug-search" style={{ position: 'absolute', width: 1, height: 1, overflow: 'hidden', clip: 'rect(0 0 0 0)' }}>약 이름이나 증상</label>
        <input id="drug-search" className="input" type="search"
          placeholder="약 이름이나 증상을 말해 보세요 (예: 머리가 지끈거려요)"
          value={keyword} onChange={e => setKeyword(e.target.value)} />
        <button type="submit" className="btn btn-primary" disabled={loading}>검색</button>
      </form>

      {q === '' && (
        <section style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          <p className="muted" style={{ margin: 0 }}>약 이름이나 증상을 그대로 적으면 AI가 알아듣고 찾아요. 예를 들어 보세요.</p>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
            {EXAMPLES.map(text => (
              <button key={text} type="button" className="btn btn-secondary" onClick={() => search(text)}>{text}</button>
            ))}
          </div>
        </section>
      )}

      {loading && <Loading text="약을 찾는 중이에요" />}
      {!loading && answer.error && <ErrorMessage message={answer.error} onRetry={() => setRetry(r => r + 1)} />}

      {showResult && !found && (
        <AlertBox type="info" title="약 이름이나 증상을 알아듣지 못했어요">
          <p>"타이레놀"처럼 약 이름을 쓰거나 "머리가 아파요"처럼 증상을 적어 보세요.</p>
        </AlertBox>
      )}

      {showResult && found && (
        <p style={{ margin: 0, color: 'var(--text-muted)' }}>
          <strong style={{ color: 'var(--text)' }}>'{found}'</strong>
          {ingredient && (ingredientEn ? ` (${ingredientEn}) 성분이 든 약` : ' 성분이 든 약')}
          {company && ' 회사의 약'}
          {symptom && '이(가) 효능에 적힌 약'}
          {drugName && ' 검색 결과'} {answer.total}건
          {totalPages > 1 && ` · ${page} / ${totalPages}쪽`}
          {drugName && answer.total > 0 && ' · 이름이 검색어로 시작하는 약을 먼저 보여드려요'}
        </p>
      )}

      {showResult && ingredient && ingredientAll > 100 && (
        <AlertBox type="info" title="앞 100건만 보여 드려요">
          <p>식약처 허가 목록에 이 성분이 든 약이 {ingredientAll.toLocaleString()}건 있어요. 그중 앞 100건에서 지금 판매 중인 {answer.total}건을 보여 드려요. 찾는 약이 없으면 약 이름으로 검색해 보세요.</p>
        </AlertBox>
      )}

      {showResult && symptom && answer.total > 0 && (
        <AlertBox type="info" title="추천 목록이 아니에요">
          <p>효능에 '{symptom}'이(가) 적힌 약을 모았어요. 순서는 추천 순위가 아니에요. 약 선택은 약사와 상담하세요.</p>
        </AlertBox>
      )}

      {showResult && found && answer.total === 0 && (
        <AlertBox type="info" title="검색 결과가 없어요">
          <p>식약처에 허가된 약 중에 찾지 못했어요. 이름을 다시 확인하거나 약사와 상담해 보세요.</p>
        </AlertBox>
      )}

      {showResult && answer.items.length > 0 && (
        // 화면 4단계 (11/11): 카드를 하나씩 띄우는 대신 한 판 안의 줄 목록. 줄 전체를 누르면 상세로 가요
        <section aria-label="검색 결과" className="result-list">
          {answer.items.map(drug => (
            <Link key={drug.item_seq} to={`/drugs/${drug.item_seq}`} className="result-row">
              <DrugImage src={drug.item_image} alt={drug.item_name} size={56} />
              <div className="result-row-text">
                <span className="result-row-name">{drug.item_name}</span>
                <span className="muted">{drug.entp_name}</span>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6}}>
                  <Badge type="notice">{drug.etc_otc ?? '일반의약품'}</Badge>
                  {drug.has_easy === false && <Badge type="none">쉬운 설명 없음</Badge>}
                  <DurBadges itemSeq={drug.item_seq} />
                </div>
              </div>
              <svg className="result-row-arrow" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor"
                strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                <path d="M9 6l6 6-6 6" />
              </svg>
            </Link>
          ))}
        </section>
      )}

      {showResult && totalPages > 1 && (
        <nav style={{ display: 'flex', flexWrap: 'wrap', justifyContent: 'center', gap: 6 }} aria-label="검색 결과 쪽">
          <button type="button" className="btn btn-secondary" onClick={() => goPage(page - 1)} disabled={page <= 1}>이전</button>
          {pages.map(p => (
            <button key={p} type="button" onClick={() => p !== page && goPage(p)}
              className={p === page ? 'btn btn-primary' : 'btn btn-secondary'} style={PAGE_BTN}
              aria-current={p === page ? 'page' : undefined}>{p}</button>
          ))}
          <button type="button" className="btn btn-secondary" onClick={() => goPage(page + 1)} disabled={page >= totalPages}>다음</button>
        </nav>
      )}
    </div>
  )
}
export default DrugSearch
