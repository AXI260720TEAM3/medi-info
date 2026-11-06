import GLOSSARY from '../data/glossary.json'

// 어려운 말 풀이: <TermNotes texts={['원문', ...]} />
// 원문은 그대로 두고, 원문에 나온 말의 풀이만 아래에 보여 줘요
// 풀이는 data/glossary.json에 있어요. words는 원문에 나오는 표기들이고, 띄어쓰기를 지운 원문과 비교해요
// except는 words가 들어 있지만 뜻이 다른 낱말이에요 (예: 경구개). 이 낱말을 지운 뒤 비교해요
function hasTerm(entry, joined) {
  const text = (entry.except || []).reduce((rest, word) => rest.replaceAll(word, ' '), joined)
  return entry.words.some(word => text.includes(word))
}

function TermNotes({ texts }) {
  const joined = texts.join(' ').replace(/\s/g, '')
  const found = GLOSSARY.filter(entry => hasTerm(entry, joined))
  if (found.length === 0) return null

  return (
    <details style={{ marginTop: 8 }}>
      <summary>어려운 말 풀이 {found.length}개</summary>
      <dl style={{ margin: '8px 0 0' }}>
        {found.map(entry => (
          <div key={entry.term} style={{ marginBottom: 6 }}>
            <dt style={{ fontWeight: 600 }}>{entry.term}</dt>
            <dd style={{ margin: 0 }}>{entry.meaning}</dd>
          </div>
        ))}
      </dl>
      <p className="muted" style={{ marginTop: 8 }}>
        약바로가 쉽게 풀어 쓴 설명이에요. 공식 내용은 위의 원문을 기준으로 확인하세요.
      </p>
    </details>
  )
}
export default TermNotes
