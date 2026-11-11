import { useState } from 'react'
import { Link, useNavigate } from 'react-router'
import OpenPharmacies from '../components/OpenPharmacies'

// 첫 화면 (11/11, 시안 design/yakbaro-mockup 홈): 큰 검색 → 할 수 있는 일 3칸 → 가까운 문 연 약국 · 119 안내
// 검색은 약 찾기 화면(/drugs?q=)으로 넘겨요. 약국은 채팅과 같은 부품(OpenPharmacies)을 써요
const EXAMPLES = ['타이레놀', '콧물이 나요', '속이 쓰려요']

const ICONS = {
  chat: <path d="M4 5h16v11H9l-5 4z" />,
  pill: <><rect x="3" y="9" width="18" height="6" rx="3" transform="rotate(-45 12 12)" /><path d="M9.5 9.5l5 5" /></>,
  pin: <><path d="M12 21s-7-6.2-7-11a7 7 0 0114 0c0 4.8-7 11-7 11z" /><circle cx="12" cy="10" r="2.5" /></>,
}

const CARDS = [
  { to: '/chat', icon: 'chat', title: 'AI에게 물어보기', text: '"하루에 몇 번 먹어요?"처럼 물으면 공식 자료로 답해요' },
  { to: '/my-meds', icon: 'pill', title: '함께 먹어도 될까?', text: '먹는 약을 담으면 짝마다 식약처 DUR로 확인해요' },
  { to: '/pharmacy', icon: 'pin', title: '지금 문 연 약국', text: '가까운 순서로, 오늘 몇 시까지 여는지 보여 드려요' },
]

function Home() {
  const navigate = useNavigate()
  const [keyword, setKeyword] = useState('')

  const search = text => {
    const q = text.trim()
    if (q) navigate(`/drugs?q=${encodeURIComponent(q)}`)
  }

  return (
    <div className="home">
      <section className="home-hero">
        <span className="home-badge">식약처 공식 자료로 답하는 약 정보</span>
        <h1 className="home-title">어떤 약이 궁금하세요?</h1>
        <p className="home-lead">
          약 이름이나 증상을 말하듯이 적어 보세요. 함께 먹어도 되는지, 지금 문 연 약국은 어디인지도 알려 드려요.
        </p>
        <form className="home-search" onSubmit={e => { e.preventDefault(); search(keyword) }}>
          <label htmlFor="home-search" className="sr-only">약 이름이나 증상</label>
          <input id="home-search" className="input" type="search" placeholder="예: 타이레놀, 머리가 지끈거려요"
            value={keyword} onChange={e => setKeyword(e.target.value)} />
          <button type="submit" className="btn btn-primary">찾기</button>
        </form>
        <div className="home-examples">
          <span className="muted">자주 찾는 말</span>
          {EXAMPLES.map(text => (
            <button key={text} type="button" className="home-example" onClick={() => search(text)}>{text}</button>
          ))}
        </div>
      </section>

      <section className="home-cards" aria-label="할 수 있는 일">
        {CARDS.map(card => (
          <Link key={card.to} to={card.to} className="home-card">
            <span className="page-title-icon" aria-hidden="true">
              <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor"
                strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                {ICONS[card.icon]}
              </svg>
            </span>
            <strong className="home-card-title">{card.title}</strong>
            <span className="home-card-text">{card.text}</span>
          </Link>
        ))}
      </section>

      <section className="home-bottom">
        <div className="home-pharmacy">
          <OpenPharmacies />
        </div>
        <aside className="home-alert" aria-label="응급 안내">
          <strong className="home-alert-title">이럴 땐 바로 119·응급실로</strong>
          <p style={{ margin: 0 }}>
            숨이 차거나 가슴이 조일 때, 약을 한꺼번에 많이 먹었을 때는 검색하지 말고 바로 도움을 받으세요.
          </p>
          <span className="home-alert-note">약바로는 진단이나 처방을 하지 않아요</span>
        </aside>
      </section>
    </div>
  )
}
export default Home
