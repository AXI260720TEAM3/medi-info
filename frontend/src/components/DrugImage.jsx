// 낱알 사진. 사진이 없으면 회색 알약 아이콘을 보여 줘요
// <DrugImage src={drug.item_image} alt={drug.item_name} size={72} />
function DrugImage({ src, alt, size = 72 }) {
  return (
    <div style={{ width: size, height: size, flex: 'none', borderRadius: size >= 90 ? 16 : 12, overflow: 'hidden', background: 'var(--surface-muted)', color: 'var(--text-muted)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
      {src
        ? <img src={src} alt={`${alt} 낱알 사진`} loading="lazy" style={{ width: '100%', height: '100%', objectFit: 'contain' }} />
        : (
          <svg width={Math.round(size * 0.42)} height={Math.round(size * 0.42)} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" aria-hidden="true">
            <rect x="3" y="9" width="18" height="6" rx="3" transform="rotate(-45 12 12)" />
            <path d="M9.5 9.5l5 5" />
          </svg>
        )}
    </div>
  )
}
export default DrugImage
