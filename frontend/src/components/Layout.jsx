import { useEffect, useState } from 'react'
import { Link, NavLink, Outlet, useNavigate } from 'react-router'

// 상단 메뉴: 새 화면을 만들면 여기에 한 줄 추가해요
// icon은 휴대폰 아래 탭에 그려요 (화면 5단계, 11/11). 제목 띠(PageTitle)와 같은 모양
const MENU = [
  { to: '/drugs', label: '검색', icon: <><circle cx="11" cy="11" r="7" /><path d="M20 20l-4-4" /></> },
  { to: '/chat', label: 'AI 질문', icon: <path d="M4 5h16v11H9l-5 4z" /> },
  { to: '/my-meds', label: '내 약', icon: <><rect x="3" y="9" width="18" height="6" rx="3" transform="rotate(-45 12 12)" /><path d="M9.5 9.5l5 5" /></> },
  { to: '/pharmacy', label: '약국', icon: <><path d="M12 21s-7-6.2-7-11a7 7 0 0114 0c0 4.8-7 11-7 11z" /><circle cx="12" cy="10" r="2.5" /></> },
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
        <Link to="/" className="logo">
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
        <div className="header-account">
          {user ? (<>
            {user.role === 'admin' && <Link to="/admin">관리자</Link>}
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

    {/* 휴대폰 아래 탭 (640px 이하에서만 보여요. 넓은 화면은 위쪽 메뉴) */}
    <nav className="tabbar" aria-label="주요 메뉴 (아래 탭)">
      {MENU.map(m => (
        <NavLink key={m.to} to={m.to}>
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"
            strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            {m.icon}
          </svg>
          {m.label}
        </NavLink>
      ))}
    </nav>

    <footer className="footer">
      <div className="footer-inner">
        <span>식약처 e약은요와 의약품 허가정보를 보여드려요. 진단이나 처방이 아니에요.</span>
        <span><Link to="/privacy">개인정보 처리방침</Link></span>
      </div>
    </footer>
  </>)
}
export default Layout
