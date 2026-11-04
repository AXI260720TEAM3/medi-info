import { Link } from 'react-router'

// 출처 표시: <SourceChip>식약처 e약은요 · 갱신 2026-06-29</SourceChip>
// to를 주면 누를 수 있어요: <SourceChip to="/drugs/202005623">근거1 · 타이레놀정500밀리그람 · 사용법</SourceChip>
function SourceChip({ to, children }) {
  const icon = (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinejoin="round" aria-hidden="true">
      <path d="M14 3H6v18h12V7z" />
      <path d="M14 3v4h4" />
    </svg>
  )
  if (to) return <Link to={to} className="source-chip">{icon}{children}</Link>
  return <span className="source-chip">{icon}{children}</span>
}
export default SourceChip
