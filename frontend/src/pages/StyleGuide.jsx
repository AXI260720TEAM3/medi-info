import Loading from '../components/Loading'
import ErrorMessage from '../components/ErrorMessage'

// 공통 UI 견본: localhost:5173/style-guide
// 화면을 만들 때 여기서 모양을 보고, 아래 코드를 복사해서 쓰면 돼요

// 경고 4종 색 조합 (AlertBox를 만들 때 참고)
const ALERTS = [
  { name: '위험 차단', text: '위험 증상이에요. 바로 119에 연락하세요.', style: { background: 'var(--danger)', color: '#FFFFFF' } },
  { name: '금기', text: '함께 먹으면 안 되는 조합이에요.', style: { background: 'var(--danger-bg)', border: '1.5px solid var(--danger)', color: 'var(--danger-text)' } },
  { name: '주의', text: '같은 성분이 겹쳐요. 하루 최대량을 확인하세요.', style: { background: 'var(--caution-bg)', border: '1.5px solid var(--caution)', color: 'var(--caution-text)' } },
  { name: '안내', text: '진단이나 처방이 아니에요.', style: { background: 'var(--info-bg)', border: '1px solid var(--info-border)', color: 'var(--info-text)' } },
]

const DRUGS = [
  { seq: '1', name: '타이레놀정500밀리그람(아세트아미노펜)', entp: '켄뷰코리아판매유한회사' },
  { seq: '2', name: '게보린정', entp: '삼진제약(주)' },
]

function StyleGuide() {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 32 }}>
      <section>
        <h1 className="title">공통 UI 견본</h1>
        <p className="muted">화면을 만들 때 이 모양과 className을 그대로 써요.</p>
      </section>

      <section style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
        <h2 className="card-title">1. 버튼</h2>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
          <button type="button" className="btn btn-primary">기본 버튼</button>
          <button type="button" className="btn btn-secondary">보조 버튼</button>
          <button type="button" className="btn btn-primary" disabled>누를 수 없음</button>
        </div>
      </section>

      <section style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
        <h2 className="card-title">2. 입력칸 + 버튼 (검색창)</h2>
        <form style={{ display: 'flex', gap: 8 }} onSubmit={e => e.preventDefault()}>
          <input className="input" placeholder="약 이름이나 증상을 말해 보세요" />
          <button type="submit" className="btn btn-primary">검색</button>
        </form>
      </section>

      <section style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
        <h2 className="card-title">3. 카드 목록</h2>
        {DRUGS.map(d => (
          <article key={d.seq} className="card" style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', justifyContent: 'space-between', gap: 12 }}>
            <div>
              <h3 className="card-title">{d.name}</h3>
              <p className="muted" style={{ margin: 0 }}>{d.entp}</p>
            </div>
            <div style={{ display: 'flex', gap: 8 }}>
              <button type="button" className="btn btn-secondary">내 약에 추가</button>
              <button type="button" className="btn btn-primary">상세 보기</button>
            </div>
          </article>
        ))}
      </section>

      <section style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
        <h2 className="card-title">4. 폼 카드 (로그인 같은 화면)</h2>
        <form className="card" style={{ maxWidth: 400, display: 'flex', flexDirection: 'column', gap: 12 }} onSubmit={e => e.preventDefault()}>
          <label style={{ display: 'flex', flexDirection: 'column', gap: 6, fontWeight: 700 }}>
            아이디
            <input className="input" />
          </label>
          <label style={{ display: 'flex', flexDirection: 'column', gap: 6, fontWeight: 700 }}>
            비밀번호
            <input className="input" type="password" />
          </label>
          <button type="submit" className="btn btn-primary">로그인</button>
        </form>
      </section>

      <section style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
        <h2 className="card-title">5. 불러오는 중 · 오류</h2>
        <Loading />
        <ErrorMessage message="약 정보 서버가 응답하지 않아요. 잠시 후 다시 시도해 주세요." onRetry={() => {}} />
      </section>

      <section style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
        <h2 className="card-title">6. 경고 4종 색 (AlertBox 참고용)</h2>
        {ALERTS.map(a => (
          <div key={a.name} style={{ ...a.style, padding: '12px 14px', borderRadius: 12, fontWeight: 700 }}>
            {a.name} · {a.text}
          </div>
        ))}
      </section>
    </div>
  )
}
export default StyleGuide
