// 약에 붙이는 작은 표시: <Badge type="caution">서방정 · 쪼개지 않기</Badge>
// type: taboo(금기) · caution(주의) · notice(알림, 성분) · none(정보 없음)
// 빨강·주황은 경고에만 써요. "안전", "추천" 같은 말은 배지에 쓰지 않아요
function Badge({ type = 'notice', children }) {
  return <span className={`badge badge-${type}`}>{children}</span>
}
export default Badge
