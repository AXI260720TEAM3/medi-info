import { useEffect, useState } from 'react'
import { Link, NavLink, Outlet, useNavigate } from 'react-router'

// 상단 메뉴: 새 화면을 만들면 여기에 한 줄 추가해요
const MENU = [
  { to: '/drugs', label: '검색' },
  { to: '/chat', label: 'AI 질문' },
  { to: '/my-meds', label: '내 약' },
  { to: '/pharmacy', label: '약국' },
]

function Layout() {
  const navigate = useNavigate()
  const [user, setUser] = useState(null) // null이면 로그인 안 한 상태

  // 화면이 처음 열릴 때 한 번: 지금 로그인한 사람이 누구인지 물어봐요
  useEffect(() =>{
    fetch('/api/auth/me')
      .then(res => (res.ok ? res.json() : null))
      .then(data => setUser(data))
      .catch(() => setUser(null))
  }, [])

  const handleLogout = async () => {
    await fetch('/api/auth/logout', { method: 'POST' })
    setUser(null)
    navigate('/drugs')
  }

  return (<>
    <header className="header">
      <div className="header-inner">
        <Link to="/drugs" className="logo">
          <span className="logo-mark">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
              <rect x="3" y="9" width="18" height="6" rx="3" transform="rotate(-45 12 12)" />
              <path d="M9.5 9.5l5 5" />
            </svg>
          </span>
          약바로
        </Link>
        <nav className="nav" aria-label="주요 메뉴">
          {MENU.map(m => <NavLink key={m.to} to={m.to}>{m.label}</NavLink>)}
        </nav>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          {user ? (<>
            <Link to="/account">{user.display_name}님</Link>
            <button type="button" className="btn btn-secondary" onClick={handleLogout}>로그아웃</button>
          </>) :(
            <Link to="/login" className="btn btn-secondary">로그인</Link>
          )}
        </div>
      </div>
    </header>

    <main className="page">
      <Outlet context={{ user, setUser }} />
    </main>

    <footer className="footer">
      <div className="footer-inner">
        <span>식약처 e약은요에 등록된 일반의약품 정보를 보여드려요. 진단이나 처방이 아니에요.</span>
        <span>로컬 AI · 질문이 PC 밖으로 나가지 않아요</span>
      </div>
    </footer>
  </>)
}
export default Layout
