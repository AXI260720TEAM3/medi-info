import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router'
import Loading from '../components/Loading'
import ErrorMessage from '../components/ErrorMessage'
import AlertBox from '../components/AlertBox'
import Badge from '../components/Badge'
import SourceChip from '../components/SourceChip'

// 펼침 목록 (시안 WEB-03). '경고'는 목록에서 빼고 맨 위 주의 상자로 올렸어요
const SECTIONS = [
  ['efcy', '효능'],
  ['use_method', '사용법'],
  ['atpn', '주의사항'],
  ['intrc', '상호작용'],
  ['se', '부작용'],
  ['deposit', '보관법'],
]
const OPEN_FIRST = ['efcy', 'use_method']   // 처음부터 펼쳐 둘 항목

const COLUMN = { display: 'flex', flexDirection: 'column', gap: 16 }
const FOLD_ROW = { display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12, minHeight: 56, padding: '0 20px', fontSize: 18, fontWeight: 700, cursor: 'pointer' }

function Chevron({ up }) {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="var(--text-muted)" strokeWidth="2" strokeLinecap="round" aria-hidden="true">
      <path d={up ? 'M6 15l6-6 6 6' : 'M6 9l6 6 6-6'} />
    </svg>
  )
}

function PillIcon({ size }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" aria-hidden="true">
      <rect x="3" y="9" width="18" height="6" rx="3" transform="rotate(-45 12 12)" />
      <path d="M9.5 9.5l5 5" />
    </svg>
  )
}

const hasText = value => typeof value === 'string' && value.trim() !== ''

function DrugDetail() {
  const { itemSeq } = useParams()
  const navigate = useNavigate()
  const [answer, setAnswer] = useState({ seq: '', drug: null, error: '' })
  const [ingredients, setIngredients] = useState({ seq: '', names: null, error: false })
  const [open, setOpen] = useState(OPEN_FIRST)
  const [message, setMessage] = useState('')
  const [retry, setRetry] = useState(0)
  const loading = answer.seq !== itemSeq

  useEffect(() => {
    fetch(`/api/drugs/${itemSeq}`)
      .then(async res => {
        const data = await res.json().catch(() => ({}))
        if (!res.ok) throw new Error(typeof data.detail === 'string' ? data.detail : '약 정보를 불러오지 못했어요.')
        setAnswer({ seq: itemSeq, drug: data, error: '' })
      })
      .catch(err => setAnswer({ seq: itemSeq, drug: null, error: err.message }))
  }, [itemSeq, retry])

  // 성분은 다른 공공 API에서 따로 가져와요. 실패해도 상세는 그대로 보여요
  useEffect(() => {
    fetch(`/api/drugs/${itemSeq}/ingredients`)
      .then(async res => {
        if (!res.ok) throw new Error()
        const data = await res.json()
        setIngredients({ seq: itemSeq, names: data.ingredients, error: false })
      })
      .catch(() => setIngredients({ seq: itemSeq, names: null, error: true }))
  }, [itemSeq])

  if (loading) return <Loading />
  if (answer.error) return <ErrorMessage message={answer.error} onRetry={() => setRetry(r => r + 1)} />

  const drug = answer.drug
  const ingredientsLoading = ingredients.seq !== itemSeq

  const toggle = key => setOpen(keys => (keys.includes(key) ? keys.filter(k => k !== key) : [...keys, key]))

  const handleAdd = async () => {
    setMessage('')
    try {
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
    } catch {
      setMessage('등록하지 못했어요. 잠시 후 다시 시도해 주세요.')
    }
  }

  const chatLink = `/chat?item_seq=${encodeURIComponent(itemSeq)}&drug_name=${encodeURIComponent(drug.item_name)}`

  return (
    <div style={COLUMN}>
      <div>
        <button type="button" className="btn btn-secondary" onClick={() => navigate(-1)}>← 목록으로</button>
      </div>

      <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'flex-start', gap: 24 }}>
        <div style={{ ...COLUMN, flex: '999 1 520px', minWidth: 0 }}>
          <section className="card" style={{ ...COLUMN, padding: 24, borderRadius: 16 }}>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 20 }}>
              <div style={{ width: 96, height: 96, flex: 'none', borderRadius: 16, overflow: 'hidden', background: 'var(--surface-muted)', color: 'var(--text-muted)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                {drug.item_image
                  ? <img src={drug.item_image} alt={`${drug.item_name} 낱알 사진`} style={{ width: '100%', height: '100%', objectFit: 'contain' }} />
                  : <PillIcon size={40} />}
              </div>
              <div style={{ flex: '1 1 260px', minWidth: 0, display: 'flex', flexDirection: 'column', gap: 6 }}>
                <h1 className="title" style={{ lineHeight: 1.35, overflowWrap: 'anywhere' }}>{drug.item_name}</h1>
                <span className="muted">{drug.entp_name}</span>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                  {ingredientsLoading && <span className="muted">성분을 확인하는 중이에요</span>}
                  {!ingredientsLoading && ingredients.error && <span className="muted">성분 정보를 불러오지 못했어요</span>}
                  {!ingredientsLoading && ingredients.names?.length === 0 && <Badge type="none">성분 정보 없음</Badge>}
                  {!ingredientsLoading && ingredients.names?.map(name => <Badge key={name} type="notice">성분 · {name}</Badge>)}
                </div>
              </div>
            </div>

            {hasText(drug.atpn_warn)
              ? (
                <AlertBox type="caution" title="경고">
                  <p style={{ whiteSpace: 'pre-line', lineHeight: 1.6 }}>{drug.atpn_warn.trim()}</p>
                </AlertBox>
              )
              : <div><Badge type="none">경고 · 정보 없음</Badge></div>}
          </section>

          <section className="card" style={{ padding: 0, borderRadius: 16, overflow: 'hidden' }}>
            {SECTIONS.map(([key, title], i) => {
              const last = i === SECTIONS.length - 1
              const line = last ? {} : { borderBottom: '1px solid var(--surface-muted)' }
              if (!hasText(drug[key])) {
                return (
                  <div key={key} style={{ ...FOLD_ROW, ...line, cursor: 'default' }}>
                    {title}
                    <Badge type="none">정보 없음</Badge>
                  </div>
                )
              }
              const isOpen = open.includes(key)
              return (
                <div key={key} style={line}>
                  <button type="button" onClick={() => toggle(key)} aria-expanded={isOpen}
                    style={{ ...FOLD_ROW, width: '100%', border: 0, background: 'transparent', font: 'inherit', color: 'var(--text)', textAlign: 'left' }}>
                    {title}
                    <Chevron up={isOpen} />
                  </button>
                  {isOpen && (
                    <p style={{ margin: 0, padding: '0 20px 18px', lineHeight: 1.7, whiteSpace: 'pre-line', color: 'var(--text)' }}>
                      {drug[key].trim()}
                    </p>
                  )}
                </div>
              )
            })}
          </section>
        </div>

        <aside style={{ flex: '1 1 280px', minWidth: 0 }}>
          <section className="card" style={{ display: 'flex', flexDirection: 'column', gap: 10, padding: 20, borderRadius: 16 }}>
            <Link to={chatLink} className="btn btn-primary">이 약 질문하기</Link>
            <button type="button" className="btn btn-secondary" onClick={handleAdd}>+ 내 약에 추가</button>
            {message && <p className="muted" style={{ margin: 0 }} role="status">{message}</p>}
            <SourceChip>식약처 e약은요 · 갱신 {drug.update_de || '정보 없음'}</SourceChip>
          </section>
        </aside>
      </div>
    </div>
  )
}
export default DrugDetail
