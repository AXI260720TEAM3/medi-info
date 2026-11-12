import { useState } from 'react'
import { Link, useNavigate } from 'react-router'
import OpenPharmacies from '../components/OpenPharmacies'

// 첫 화면 (11/12 시안 "찾기 상자가 주인공"): 찾기 상자 → 탭 2개 → 물어볼 수 있는 질문 → 내 약 · 약국 · 119 칸 → 문 연 약국
// "약 찾기" 탭은 약 찾기 화면(/drugs?q=)으로, "AI에게 물어보기" 탭은 AI 질문 화면에 글을 채워서 넘겨요
const MODES = {
  drug: { label: '약 이름으로 찾기', placeholder: '약 이름 (예: 타이레놀)' },
  ask: { label: 'AI에게 물어보기', placeholder: '궁금한 점 (예: 머리가 아파요)' },
}

// 누르면 AI 질문 화면에 글이 채워져요 (보내기는 사용자가 눌러요)
const QUESTIONS = [
  { text: '타이레놀은 하루에 몇 번 먹어요?', tag: '약 정보', tone: 'info' },
  { text: '임신 중인데 감기약 먹어도 돼요?', tag: '안전', tone: 'safe' },
  { text: '판콜에이랑 타이레놀 같이 먹어도 돼요?', tag: '함께 먹기', tone: 'together' },
  { text: '아이 해열제는 몇 시간 간격으로 먹여요?', tag: '약 정보', tone: 'info' },
]

function Home() {
  const navigate = useNavigate()
  const [mode, setMode] = useState('drug')
  const [keyword, setKeyword] = useState('')

  const ask = question => navigate('/chat', { state: { question } })
  const submit = () => {
    const q = keyword.trim()
    if (!q) return
    if (mode === 'drug') navigate(`/drugs?q=${encodeURIComponent(q)}`)
    else ask(q)
  }

  return (
    <div className="home">
      <h1 className="sr-only">약바로: 어떤 약이 궁금하세요?</h1>

      <form className="home-search" onSubmit={e => { e.preventDefault(); submit() }}>
        <label htmlFor="home-search" className="sr-only">{MODES[mode].label}</label>
        <input id="home-search" className="input" type="search" placeholder={MODES[mode].placeholder}
          value={keyword} onChange={e => setKeyword(e.target.value)} />
        <button type="submit" className="btn btn-primary">{mode === 'drug' ? '찾기' : '묻기'}</button>
      </form>

      <div className="home-tabs" role="group" aria-label="찾는 방법">
        {Object.entries(MODES).map(([key, m]) => (
          <button key={key} type="button" className={`home-tab${mode === key ? ' is-on' : ''}`}
            aria-pressed={mode === key} onClick={() => setMode(key)}>
            {m.label}
          </button>
        ))}
      </div>

      <section className="home-box" aria-labelledby="home-questions">
        <h2 id="home-questions" className="home-box-title">이런 걸 물어볼 수 있어요</h2>
        <ol className="home-questions">
          {QUESTIONS.map((q, i) => (
            <li key={q.text}>
              <button type="button" className="home-question" onClick={() => ask(q.text)}>
                <span className="home-question-num">{i + 1}</span>
                <span className="home-question-text">{q.text}</span>
                <span className={`home-tag is-${q.tone}`}>{q.tag}</span>
              </button>
            </li>
          ))}
        </ol>
      </section>

      <nav className="home-quick" aria-label="바로 가기">
        <Link to="/my-meds" className="home-quick-cell">
          <strong>내 약</strong>
          <span>함께 먹어도 되는지 확인</span>
        </Link>
        <Link to="/pharmacy" className="home-quick-cell">
          <strong>문 연 약국</strong>
          <span>가까운 곳 찾기</span>
        </Link>
        <a href="tel:119" className="home-quick-cell is-alert">
          <strong>급할 땐 119</strong>
          <span>숨이 차거나 약을 많이 먹었을 때</span>
        </a>
      </nav>

      <section className="home-box">
        <OpenPharmacies />
      </section>
    </div>
  )
}
export default Home
