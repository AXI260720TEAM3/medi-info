// 불러오는 중 표시: <Loading /> 또는 <Loading text="답변을 만드는 중이에요" />
function Loading({ text = '불러오는 중이에요…' }) {
  return (
    <p className="loading" role="status">
      <span className="spinner" aria-hidden="true" />
      {text}
    </p>
  )
}
export default Loading
