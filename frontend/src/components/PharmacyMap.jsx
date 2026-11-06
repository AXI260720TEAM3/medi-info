import { useState } from 'react'
import KakaoPharmacyMap from './KakaoPharmacyMap'
import LeafletPharmacyMap from './LeafletPharmacyMap'

// 약국 지도 입구. 약국 화면은 이것만 알아요 (속이 카카오인지 Leaflet인지 몰라요)
//   items: 약국 목록 (lat, lon, name, is_open)
//   start: 첫 핀 번호 (목록 번호와 같게. 2쪽이면 11)
//   myLat, myLon: 내 위치 (없으면 '')
//   selectedId: 고른 약국 id (그 핀을 파랗고 크게, 지도 가운데로)
//   onSelect(id): 핀을 눌렀을 때 약국 화면에 알려 줘요
//
// 고르는 규칙: frontend/.env.local에 VITE_KAKAO_MAP_KEY가 있으면 카카오,
//             없거나 카카오를 못 불러오면(키 오류, 등록 안 된 주소, 인터넷) Leaflet
const KAKAO_KEY = import.meta.env.VITE_KAKAO_MAP_KEY ?? ''

function PharmacyMap(props) {
  const [kakaoFailed, setKakaoFailed] = useState(false)

  if (KAKAO_KEY && !kakaoFailed) {
    return <KakaoPharmacyMap {...props} appKey={KAKAO_KEY} onFail={() => setKakaoFailed(true)} />
  }
  return <LeafletPharmacyMap {...props} />
}
export default PharmacyMap
