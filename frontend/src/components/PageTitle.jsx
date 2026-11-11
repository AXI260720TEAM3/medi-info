// 화면 맨 위 제목 띠: <PageTitle icon="search" title="약 찾기">설명 한 줄</PageTitle>
// 연한 파란 바탕 + 아이콘 상자 + 큰 제목으로, 지금 어느 화면인지 바로 보이게 해요 (11/11 화면 2단계)
// 설명(children)은 글자나 화면 조각 둘 다 돼요. 없으면 제목만 보여요

// 아이콘은 선으로 그린 SVG (위쪽 메뉴와 같은 모양)
const ICONS = {
  search: <><circle cx="11" cy="11" r="7" /><path d="M20 20l-4-4" /></>,
  chat: <path d="M4 5h16v11H9l-5 4z" />,
  pill: <><rect x="3" y="9" width="18" height="6" rx="3" transform="rotate(-45 12 12)" /><path d="M9.5 9.5l5 5" /></>,
  pin: <><path d="M12 21s-7-6.2-7-11a7 7 0 0114 0c0 4.8-7 11-7 11z" /><circle cx="12" cy="10" r="2.5" /></>,
}

function PageTitle({ icon, title, children }) {
  return (
    <header className="page-title">
      {ICONS[icon] && (
        <span className="page-title-icon" aria-hidden="true">
          <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor"
            strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
            {ICONS[icon]}
          </svg>
        </span>
      )}
      <div className="page-title-text">
        <h1 className="title">{title}</h1>
        {children && <p className="page-title-sub">{children}</p>}
      </div>
    </header>
  )
}
export default PageTitle
