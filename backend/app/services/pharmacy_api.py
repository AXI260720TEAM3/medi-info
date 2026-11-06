import xml.etree.ElementTree as ET
from datetime import datetime
from zoneinfo import ZoneInfo

import httpx
from ..config import DATA_GO_KR_KEY

# 국립중앙의료원 약국 정보 (응답은 XML만 와요)
URL = "https://apis.data.go.kr/B552657/ErmctInsttInfoInqireService/getParmacyListInfoInqire"
KST = ZoneInfo("Asia/Seoul")   # 서버 시계가 UTC여도 한국 요일로


def _hours(item, day):
    """day(1=월 ... 7=일)의 영업시간을 '08:00~17:30' 모양으로. 쉬는 날이면 None."""
    start = item.findtext(f"dutyTime{day}s")   # 예: "0800"
    end = item.findtext(f"dutyTime{day}c")     # 예: "1730"
    if not start or not end:
        return None
    return start[:2] + ":" + start[2:] + "~" + end[:2] + ":" + end[2:]


def search_pharmacy(sido, sigungu, page=1, size=10):
    """시/도와 시/군/구로 약국 목록을 받는다. (전체 건수, 약국 목록)을 돌려준다."""
    params = {"serviceKey": DATA_GO_KR_KEY, "Q0": sido, "Q1": sigungu,
              "ORD": "NAME", "pageNo": page, "numOfRows": size}
    res = httpx.get(URL, params=params, timeout=10)
    res.raise_for_status()
    root = ET.fromstring(res.text)
    total = int(root.findtext(".//totalCount") or 0)

    today = datetime.now(KST).isoweekday()   # 1=월 ... 7=일 (API 칸 번호와 같아요)

    result = []
    for item in root.iter("item"):
        result.append({
            "id": item.findtext("hpid"),
            "name": item.findtext("dutyName"),
            "addr": item.findtext("dutyAddr"),
            "tel": item.findtext("dutyTel1"),
            "lat": item.findtext("wgs84Lat"),
            "lon": item.findtext("wgs84Lon"),
            "today_hours": _hours(item, today),
        })
    return total, result
