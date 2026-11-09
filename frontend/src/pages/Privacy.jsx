// 개인정보 처리방침 (기능명세 I-8, 11/06 기획 피드백 "개인정보법 확인")
// 숫자(보관 90일)는 backend/app/services/privacy.py 의 RETENTION_DAYS와 같아야 해요

const SECTION = { display: 'flex', flexDirection: 'column', gap: 8 }
const TABLE = { width: '100%', borderCollapse: 'collapse', fontSize: 15 }
const CELL = { padding: '10px 12px', borderBottom: '1px solid var(--border)', textAlign: 'left', verticalAlign: 'top' }

const ITEMS = [
  ['계정', '아이디, 표시 이름, 비밀번호(암호화해 저장), 이메일', '로그인, 아이디 찾기·비밀번호 재설정', '탈퇴할 때까지'],
  ['건강정보 (선택 동의)', '내 약 목록, 복용자 프로필(임신·수유·나이 등)', '함께 먹기 점검, 대상별 주의 표시', '탈퇴하거나 동의를 철회할 때까지'],
  ['동의 기록', '동의 종류, 약관 버전, 동의 시각', '동의 사실 확인', '탈퇴하거나 철회할 때까지'],
  ['이메일 인증번호', '이메일, 인증번호(암호화), 만료 시각', '가입·계정 찾기 본인 확인', '탈퇴할 때 삭제 (10분 뒤 사용 불가)'],
  ['AI 질문 기록', '질문과 답변 글. 누구의 질문인지는 저장하지 않아요. 전화번호·이메일·주민번호 모양은 가려서 저장해요', '안전장치 점검, 답변 품질 평가', '90일 뒤 자동 삭제'],
]

function Privacy() {
  return (
    <article style={{ display: 'flex', flexDirection: 'column', gap: 24, maxWidth: 820 }}>
      <header style={SECTION}>
        <h1 className="title">개인정보 처리방침</h1>
        <p className="muted" style={{ margin: 0 }}>약바로는 필요한 정보만 받고, 쓰임이 끝나면 지워요. (시행일 2026-11-09)</p>
      </header>

      <section style={SECTION} aria-labelledby="p-items">
        <h2 id="p-items" className="card-title">1. 무엇을, 왜, 언제까지</h2>
        <div className="table-card">
          <table style={TABLE}>
            <thead>
              <tr>{['구분', '항목', '목적', '보관 기간'].map(h => <th key={h} style={{ ...CELL, color: 'var(--text-muted)', fontSize: 14 }}>{h}</th>)}</tr>
            </thead>
            <tbody>
              {ITEMS.map(row => (
                <tr key={row[0]}>{row.map((c, i) => <td key={i} style={{ ...CELL, fontWeight: i === 0 ? 700 : 400 }}>{c}</td>)}</tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section style={SECTION} aria-labelledby="p-health">
        <h2 id="p-health" className="card-title">2. 건강정보는 따로 동의를 받아요</h2>
        <p style={{ margin: 0 }}>내 약 목록과 프로필은 건강에 관한 정보라서, 개인정보 동의와 <b>따로</b> 동의를 받아요. 동의하지 않아도 가입하고 약 검색·AI 질문은 쓸 수 있어요. 내 정보 화면에서 언제든 동의를 철회할 수 있고, 철회하면 내 약 목록과 프로필을 바로 지워요.</p>
      </section>

      <section style={SECTION} aria-labelledby="p-ai">
        <h2 id="p-ai" className="card-title">3. AI 질문은 PC 밖으로 나가지 않아요</h2>
        <p style={{ margin: 0 }}>AI 답변은 서비스 컴퓨터 안의 로컬 AI가 만들어요. 질문을 외부 AI 회사로 보내지 않아요. 약 정보는 식약처·국립중앙의료원 공공 API에서 그때그때 가져오고, 따로 모아 두지 않아요.</p>
      </section>

      <section style={SECTION} aria-labelledby="p-delete">
        <h2 id="p-delete" className="card-title">4. 지우는 방법</h2>
        <ul style={{ margin: 0, paddingLeft: 20, display: 'flex', flexDirection: 'column', gap: 4 }}>
          <li>내 정보 화면 → 건강정보 동의 철회: 내 약 목록·프로필 삭제</li>
          <li>내 정보 화면 → 회원 탈퇴(비밀번호 확인): 계정과 위 정보 모두 삭제</li>
          <li>AI 질문 기록은 누구의 것인지 저장하지 않아서, 90일이 지나면 모두 자동으로 지워요</li>
        </ul>
      </section>

      <section style={SECTION} aria-labelledby="p-etc">
        <h2 id="p-etc" className="card-title">5. 그 밖에</h2>
        <p style={{ margin: 0 }}>이 서비스는 교육용 팀 프로젝트예요. 실제 진단이나 처방을 하지 않고, 시연에는 실제 개인의 복용 기록을 쓰지 않아요.</p>
      </section>
    </article>
  )
}
export default Privacy
