// 약봉지 사진 공용 도구: 내 약(MedScan)과 AI 질문(ChatScan)이 같이 써요
export const MAX_BYTES = 20 * 1024 * 1024  // 고르는 원본 사진. 보낼 때는 줄여서 보내요
const MAX_SIDE = 1600  // 사진을 읽는 AI는 한 번에 받을 수 있는 양이 정해져 있어서, 폰 사진(4000px)은 그대로 보내면 거절해요

// '게보린정(수출명:돌로린정)' -> '게보린정'
export const baseName = itemName => itemName.split('(')[0].trim()

// 긴 쪽이 MAX_SIDE를 넘으면 줄여서 JPG 글자(data:image/jpeg;base64,...)로 바꿔요
export function shrinkImage(file) {
  return new Promise((resolve, reject) => {
    const url = URL.createObjectURL(file)
    const img = new Image()
    img.onload = () => {
      const scale = Math.min(1, MAX_SIDE / Math.max(img.width, img.height))
      const canvas = document.createElement('canvas')
      canvas.width = Math.round(img.width * scale)
      canvas.height = Math.round(img.height * scale)
      canvas.getContext('2d').drawImage(img, 0, 0, canvas.width, canvas.height)
      URL.revokeObjectURL(url)
      resolve(canvas.toDataURL('image/jpeg', 0.9))
    }
    img.onerror = () => {
      URL.revokeObjectURL(url)
      reject(new Error('사진 열기 실패'))
    }
    img.src = url
  })
}
