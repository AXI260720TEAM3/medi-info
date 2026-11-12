// 약의 위험 경고: <AlertBox type="caution" title="주의가 필요해요">이유</AlertBox>
// type: danger(위험 차단) · taboo(금기) · caution(주의) · info(안내)
// 서버 오류 같은 안내는 이게 아니라 ErrorMessage를 써요
// 제목 앞 그림은 이모지 대신 종류별 선 아이콘을 그려요 (11/11). 색 말고 모양으로도 구분돼요
const ICONS = {
  danger: <><circle cx="12" cy="12" r="9" /><path d="M9 9l6 6M15 9l-6 6" /></>,
  taboo: <><circle cx="12" cy="12" r="9" /><path d="M9 9l6 6M15 9l-6 6" /></>,
  caution: <><path d="M10.3 3.9L1.8 18a2 2 0 001.7 3h17a2 2 0 001.7-3L13.7 3.9a2 2 0 00-3.4 0z" /><path d="M12 9v4M12 17h.01" /></>,
  info: <><circle cx="12" cy="12" r="9" /><path d="M12 11v5M12 8h.01" /></>,
}

function AlertBox({ type = 'info', title, children }) {
  const urgent = type === 'danger' || type === 'taboo'
  return (
    <div className={`alert-box alert-${type}`} role={urgent ? 'alert' : 'status'}>
      {title && (
        <p className="alert-title">
          <svg className="alert-icon" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor"
            strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            {ICONS[type] ?? ICONS.info}
          </svg>
          <span>{title}</span>
        </p>
      )}
      {children}
    </div>
  )
}
export default AlertBox
