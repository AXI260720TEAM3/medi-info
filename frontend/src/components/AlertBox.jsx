// 약의 위험 경고: <AlertBox type="caution" title="주의가 필요해요">이유</AlertBox>
// type: danger(위험 차단) · taboo(금기) · caution(주의) · info(안내)
// 서버 오류 같은 안내는 이게 아니라 ErrorMessage를 써요
function AlertBox({ type = 'info', title, children }) {
  const urgent = type === 'danger' || type === 'taboo'
  return (
    <div className={`alert-box alert-${type}`} role={urgent ? 'alert' : 'status'}>
      {title && <p className="alert-title">{title}</p>}
      {children}
    </div>
  )
}
export default AlertBox
