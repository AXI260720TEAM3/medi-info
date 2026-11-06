// 약국 거리·문구 (약국 화면과 채팅의 "지금 문 연 약국"이 함께 써요)

// 위치 API가 주는 거리(km 글자, 예: "0.12")를 사람이 읽기 쉬운 글자로
export function formatDistance(km) {
  const n = Number(km)
  if (n < 1) return `${Math.round(n * 1000)}m`
  return `${n.toFixed(1)}km`
}
