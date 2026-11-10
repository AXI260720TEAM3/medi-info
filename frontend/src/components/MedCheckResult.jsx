import AlertBox from './AlertBox'
import SourceChip from './SourceChip'
import TermNotes from './TermNotes'

// 함께 먹기 판정 결과 카드: <MedCheckResult answer={응답} />
// answer는 /api/my-meds/check, /api/interactions/check, AI 질문 응답의 interaction과 같은 모양이에요
//   { level, results: [{ item_seq_a, item_name_a, item_seq_b, item_name_b, level, reasons, basis }] }
// 내 약(MedCheck)과 AI 질문이 같은 카드를 써서, 같은 조합이면 같은 모양으로 보여요 (E안 7번)
//
// 판정별 표시와 경고 종류. 색만으로 구분하지 않게 글자로도 판정을 적어요
const RESULTS = {
  block: { icon: '🔴', type: 'taboo', label: '함께 먹으면 안 돼요' },
  warn: { icon: '🟡', type: 'caution', label: '주의가 필요해요' },
  unknown: { icon: '🟡', type: 'caution', label: '확인을 끝내지 못했어요' },
}

const NO_FINDING = '⚪ 확인된 병용금기나 성분 겹침은 없어요.'

function MedCheckResult({
  answer,
  levels = ['block', 'warn', 'unknown'],   // 보여 줄 판정 (🔴 자동 알림은 ['block']만)
  emptyText = NO_FINDING,                   // 보여 줄 판정이 없을 때 문장. null이면 아무것도 안 보여요
  showCount = true,                         // "확인 필요 N건"
  showNote = true,                          // 아래 안내 문장
}) {
  const shownResults = (answer?.results || []).filter(result => levels.includes(result.level))

  if (shownResults.length === 0 && emptyText === null) return null

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
      {shownResults.length === 0 && <AlertBox type="info" title={emptyText} />}
      {showCount && shownResults.length > 0 && <p className="card-title">확인 필요 {shownResults.length}건</p>}
      {shownResults.map(result => {
        const shown = RESULTS[result.level]
        return (
          <AlertBox
            key={`${result.item_seq_a}-${result.item_seq_b}`}
            type={shown.type}
            title={`${shown.icon} ${result.item_name_a} + ${result.item_name_b}: ${shown.label}`}
          >
            {result.reasons.map(reason => <p key={reason}>{reason}</p>)}
            <TermNotes texts={result.reasons} />
            {result.basis.length > 0 && (
              <p style={{ marginTop: 8 }}>
                <SourceChip>판정 근거: {result.basis.join(' · ')}</SourceChip>
              </p>
            )}
          </AlertBox>
        )
      })}
      {showNote && (
        <p className="muted">
          식약처 자료에서 찾지 못한 조합이라도 문제가 없다는 뜻은 아니에요. 진단이나 처방이 아니에요. 복용 전에 약사와 상의하세요.
        </p>
      )}
    </div>
  )
}
export default MedCheckResult
