// 오류 문구: <ErrorMessage message={error} />
// onRetry를 주면 "다시 시도" 버튼이 생겨요: <ErrorMessage message={error} onRetry={() => ...} />
// 약의 위험 경고(차단·금기·주의·안내)는 이게 아니라 AlertBox를 써요
function ErrorMessage({ message, onRetry }) {
  return (
    <div className="error-box" role="alert">
      <p>{message}</p>
      {onRetry && <button type="button" className="btn btn-secondary" onClick={onRetry}>다시 시도</button>}
    </div>
  )
}
export default ErrorMessage
