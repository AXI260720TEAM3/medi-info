import xml.etree.ElementTree as ET
from datetime import datetime
from zoneinfo import ZoneInfo

import httpx
from ..config import DATA_GO_KR_KEY

# 국립중앙의료원 약국 정보 (응답은 XML만 와요)
URL = "https://apis.data.go.kr/B552657/ErmctInsttInfoInqireService/getParmacyListInfoInqire"
NEAR_URL = "https://apis.data.go.kr/B552657/ErmctInsttInfoInqireService/getParmacyLcinfoInqire"
KST = ZoneInfo("Asia/Seoul")   # 서버 시계가 UTC여도 한국 요일로
ALL_ROWS = 1000   # 지역 검색은 한 번에 다 받아요 (강남구 515곳, 약 1초)
NEAR_ROWS = 50    # 위치 검색에서 문 연 곳을 거르려고 넉넉히 (강남역 기준 약 400m)


def _time_range(start, end):
    """'0800', '1730' -> '08:00~17:30'. 둘 중 하나라도 없으면 None."""
    if not start or not end:
        return None
    return start[:2] + ":" + start[2:] + "~" + end[:2] + ":" + end[2:]


def _hours(item, day):
    """day(1=월 ... 7=일)의 영업시간을 '08:00~17:30' 모양으로. 쉬는 날이면 None."""
    start = item.findtext(f"dutyTime{day}s")   # 예: "0800"
    end = item.findtext(f"dutyTime{day}c")     # 예: "1730"
    return _time_range(start, end)


def _is_open(start, end, now):
    """start, end는 '0900', '2500' 같은 글자(없으면 None), now는 2240 같은 숫자. 지금 영업 중이면 True."""
    if not start or not end:
        return False
    return int(start) <= now < int(end)

def _close_label(end):
    """'2300' -> '오늘 23:00까지', '2500' -> '다음 날 01:00까지'. 없으면 None."""
    if not end:
        return None
    t = int(end)
    if t > 2400:                       # 24시를 넘기면 다음 날 새벽
        t -= 2400
        return f"다음 날 {t // 100:02d}:{t % 100:02d}까지"
    return f"오늘 {end[:2]}:{end[2:]}까지"


def _now():
    """한국 시간 기준 (오늘 요일 1~7, 지금 시각 2240 같은 숫자)"""
    now = datetime.now(KST)
    return now.isoweekday(), now.hour * 100 + now.minute


def search_pharmacy(sido, sigungu, page=1, size=10, open_now=False):
    """시/도와 시/군/구로 약국 목록을 받는다. (전체 건수, 약국 목록)을 돌려준다.
    open_now면 지금 문 연 곳만. 거른 뒤에 쪽을 나눠야 해서 한 번에 다 받아요."""
    params = {"serviceKey": DATA_GO_KR_KEY, "Q0": sido,
              "ORD": "NAME", "pageNo": 1, "numOfRows": ALL_ROWS}
    if sigungu:                      # 세종처럼 시/군/구가 없으면 Q1을 아예 안 보내요
        params["Q1"] = sigungu
    res = httpx.get(URL, params=params, timeout=10)
    res.raise_for_status()
    root = ET.fromstring(res.text)

    today, now = _now()

    result = []
    for item in root.iter("item"):
        start = item.findtext(f"dutyTime{today}s")
        end = item.findtext(f"dutyTime{today}c")
        result.append({
            "id": item.findtext("hpid"),
            "name": item.findtext("dutyName"),
            "addr": item.findtext("dutyAddr"),
            "tel": item.findtext("dutyTel1"),
            "lat": item.findtext("wgs84Lat"),
            "lon": item.findtext("wgs84Lon"),
            "today_hours": _time_range(start, end),
            "is_open": _is_open(start, end, now),
            "close_label": _close_label(end),
        })
    if open_now:
        result = [p for p in result if p["is_open"]]
    first = (page - 1) * size
    return len(result), result[first:first + size]


def search_nearby(lat, lon, size=10, open_now=False):
    """위도·경도에서 가까운 약국 목록. API가 가까운 순으로 줘요.
    open_now면 넉넉히 받아서 문 연 곳만 size개."""
    params = {"serviceKey": DATA_GO_KR_KEY, "WGS84_LAT": lat, "WGS84_LON": lon,
              "pageNo": 1, "numOfRows": NEAR_ROWS if open_now else size}
    res = httpx.get(NEAR_URL, params=params, timeout=10)
    res.raise_for_status()
    root = ET.fromstring(res.text)

    _, now = _now()

    result = []
    for item in root.iter("item"):
        start = item.findtext("startTime")   # 위치 API는 오늘 시각만 바로 줘요
        end = item.findtext("endTime")
        result.append({
            "id": item.findtext("hpid"),
            "name": item.findtext("dutyName"),
            "addr": item.findtext("dutyAddr"),
            "tel": item.findtext("dutyTel1"),
            "lat": item.findtext("latitude"),
            "lon": item.findtext("longitude"),
            "distance": item.findtext("distance"),
            "today_hours": _time_range(start, end),
            "is_open": _is_open(start, end, now),
            "close_label": _close_label(end),
        })
    if open_now:
        result = [p for p in result if p["is_open"]]
    return result[:size]
