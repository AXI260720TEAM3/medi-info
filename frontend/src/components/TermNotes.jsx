// 어려운 말 풀이: <TermNotes texts={['원문', ...]} />
// 원문은 그대로 두고, 원문에 나온 말의 풀이만 아래에 보여 줘요
// words: 원문에 나오는 표기들. 띄어쓰기를 지운 원문과 비교해요
const GLOSSARY = [
  { term: '병용금기', words: ['병용금기'], meaning: '함께 먹으면 안 되는 약의 조합이에요.' },
  { term: '미확립', words: ['미확립'], meaning: '아직 확인되지 않았다는 뜻이에요. 안전하다는 뜻도, 위험하다고 밝혀졌다는 뜻도 아니에요.' },
  { term: '비스테로이드성 소염제', words: ['비스테로이드성소염제'], meaning: '이부프로펜, 아스피린처럼 염증과 통증을 줄이는 약의 한 종류예요.' },
  { term: '프로스타글란딘 합성 저해제', words: ['프로스타글란딘합성저해제'], meaning: '통증과 염증에 관여하는 물질이 만들어지는 것을 막는 약이에요.' },
  { term: '횡문근융해증', words: ['횡문근융해'], meaning: '근육이 손상되어 근육 성분이 혈액으로 나오는 병이에요.' },
  { term: '근병증', words: ['근병증', '근육병증'], meaning: '근육에 생기는 병을 통틀어 부르는 말이에요.' },
  { term: '이상반응', words: ['이상반응'], meaning: '약을 먹은 뒤 나타나는 원하지 않은 반응이에요.' },
  { term: '위장관', words: ['위장관'], meaning: '위와 장처럼 음식이 지나가는 길이에요.' },
  { term: '혈액학적 독성', words: ['혈액학적독성'], meaning: '혈액 세포가 줄어드는 것처럼 혈액에 나타나는 해로운 영향이에요.' },
  { term: '혈장농도', words: ['혈장농도'], meaning: '혈액 속에 들어 있는 약의 양이에요.' },
  { term: '진정작용', words: ['진정작용'], meaning: '신경을 가라앉혀 졸리게 할 수 있는 작용이에요.' },
  { term: '중추신경', words: ['중추신경'], meaning: '뇌와 척수를 함께 부르는 말이에요.' },
  { term: 'QT 간격 연장', words: ['QT간격연장'], meaning: '심전도 검사에서 보는 심장 박동의 한 구간이 길어지는 것이에요.' },
  { term: '심실부정맥', words: ['심실부정맥'], meaning: '심장 아래쪽 방(심실)에서 시작되는 불규칙한 심장 박동이에요.' },
  { term: '동맥관 조기폐쇄', words: ['동맥관조기폐쇄', '동맥관의조기페쇄'], meaning: '태아의 혈관인 동맥관이 태어나기 전에 미리 닫히는 것이에요.' },
  { term: '동맥관 수축', words: ['동맥관수축'], meaning: '태아의 혈관인 동맥관이 좁아지는 것이에요.' },
  { term: '양수과소증', words: ['양수과소증'], meaning: '태아를 둘러싼 양수가 너무 적은 상태예요.' },
  { term: '신기능', words: ['신기능'], meaning: '콩팥의 기능이에요.' },
  { term: '신장애', words: ['신장애'], meaning: '콩팥이 제대로 일하지 못하는 상태예요.' },
  { term: '신부전', words: ['신부전'], meaning: '콩팥의 기능이 크게 떨어진 상태예요.' },
  { term: '심폐독성', words: ['심폐독성', '심폐기관독성'], meaning: '심장과 폐에 나타나는 해로운 영향이에요.' },
  { term: '폐고혈압', words: ['폐고혈압'], meaning: '폐로 가는 혈관의 혈압이 높아진 상태예요.' },
  { term: '실혈', words: ['실혈'], meaning: '피를 많이 흘리는 것이에요.' },
  { term: '항응고 작용', words: ['항응고'], meaning: '피가 굳는 것을 막는 작용이에요.' },
  { term: '태자', words: ['태자'], meaning: '배 속에서 자라는 새끼예요. 주로 동물실험에서 쓰는 말이에요.' },
  { term: '배자독성', words: ['배자독성'], meaning: '발생 초기의 배아에 나타나는 해로운 영향이에요.' },
  { term: '생식독성', words: ['생식독성'], meaning: '임신, 출산, 태아의 발달에 나타나는 해로운 영향이에요.' },
  { term: '정중배벽갈림증', words: ['정중배벽갈림증'], meaning: '태아의 배 벽 가운데가 제대로 닫히지 않는 선천 이상이에요.' },
  { term: '난산', words: ['난산'], meaning: '아기를 낳는 과정이 순조롭지 않은 것이에요.' },
  { term: '분만', words: ['분만'], meaning: '아기를 낳는 것이에요.' },
]

function TermNotes({ texts }) {
  const joined = texts.join(' ').replace(/\s/g, '')
  const found = GLOSSARY.filter(entry => entry.words.some(word => joined.includes(word)))
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
