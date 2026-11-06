import math
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from zoneinfo import ZoneInfo

import httpx
from ..config import DATA_GO_KR_KEY

# 국립중앙의료원 약국 정보 (응답은 XML만 와요)
URL = "https://apis.data.go.kr/B552657/ErmctInsttInfoInqireService/getParmacyListInfoInqire"
NEAR_URL = "https://apis.data.go.kr/B552657/ErmctInsttInfoInqireService/getParmacyLcinfoInqire"
BASS_URL = "https://apis.data.go.kr/B552657/ErmctInsttInfoInqireService/getParmacyBassInfoInqire"   # 약국 하나의 요일별 시간표
KST = ZoneInfo("Asia/Seoul")   # 서버 시계가 UTC여도 한국 요일로
ALL_ROWS = 1000   # 한 번에 받는 수 (API 최대). 강남구 515곳은 한 번, 약 1초
MAX_ROWS = 3000   # 이보다 많으면 받지 않고 지역을 고르게 해요 ("온누리" 전국 1,897곳은 OK, "약국" 25,436곳은 너무 많음)
NEAR_ROWS = 50    # 위치 검색에서 문 연 곳을 거르려고 넉넉히 (강남역 기준 약 400m)
EARLY = 800       # 이 시각(08:00) 전 새벽에만 '어제 밤부터 이어지는 영업'을 확인해요


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


def _yesterday(today):
    """어제 요일 번호. 월(1)의 어제는 일(7)"""
    return 7 if today == 1 else today - 1


def _late_night(yesterday_end, now):
    """자정 넘김 영업: 어제 닫는 시각이 24시를 넘고(예: '2500') 지금이 그 전이면 어제 영업이 아직 안 끝났어요.
    그럴 때 '오늘 01:00까지'를 돌려주고, 아니면 None.
      금요일 0900~2500, 지금 토요일 00:30 -> '오늘 01:00까지'
      금요일 0900~2500, 지금 토요일 01:10 -> None (이미 닫음)"""
    if not yesterday_end or int(yesterday_end) <= 2400:
        return None
    left = int(yesterday_end) - 2400   # 2500 -> 100 (= 01:00)
    if now >= left:
        return None
    return f"오늘 {left // 100:02d}:{left % 100:02d}까지"


def _yesterday_end(hpid, yday):
    """위치 API는 오늘 시각만 줘서, 약국 하나의 어제 닫는 시각을 기본정보 API로 따로 물어봐요.
    못 받으면 None (오늘 시간표 결과를 그대로 써요)"""
    try:
        res = httpx.get(BASS_URL, params={"serviceKey": DATA_GO_KR_KEY, "HPID": hpid}, timeout=5)
        res.raise_for_status()
        return ET.fromstring(res.text).findtext(f".//dutyTime{yday}c")
    except (httpx.HTTPError, ET.ParseError):
        return None


class TooManyPharmacies(Exception):
    """찾은 약국이 MAX_ROWS보다 많을 때. total에 전체 수를 담아 라우트가 안내 문구를 만들어요"""
    def __init__(self, total):
        super().__init__(total)
        self.total = total


def _fetch_page(params, page_no):
    """지역·이름 검색 API의 page_no쪽을 받아 (전체 건수, item 목록)"""
    res = httpx.get(URL, params={**params, "pageNo": page_no}, timeout=10)
    res.raise_for_status()
    root = ET.fromstring(res.text)
    return int(root.findtext(".//totalCount") or 0), list(root.iter("item"))


def search_pharmacy(sido="", sigungu="", page=1, size=10, open_now=False, name=""):
    """시/도·시/군/구·약국 이름으로 약국 목록을 받는다. (전체 건수, 약국 목록)을 돌려준다.
    open_now면 지금 문 연 곳만. 거른 뒤에 쪽을 나눠야 해서 한 번에 다 받아요.
    name이 있으면 시/도 없이 전국에서 찾을 수 있고, 문 연 곳이 위로 와요."""
    params = {"serviceKey": DATA_GO_KR_KEY, "ORD": "NAME", "numOfRows": ALL_ROWS}
    if sido:
        params["Q0"] = sido
    if sigungu:                      # 세종처럼 시/군/구가 없으면 Q1을 아예 안 보내요
        params["Q1"] = sigungu
    if name:
        params["QN"] = name          # 약국 이름 (부분 일치: "온누리"면 "2층온누리약국"도)
    total, items = _fetch_page(params, 1)
    if total > MAX_ROWS:
        raise TooManyPharmacies(total)
    if total > ALL_ROWS:
        count = math.ceil(total / ALL_ROWS)
        for page_no in range(2, count + 1):
            _, more = _fetch_page(params, page_no)
            items += more

    today, now = _now()
    yday = _yesterday(today)

    result = []
    for item in items:
        start = item.findtext(f"dutyTime{today}s")
        end = item.findtext(f"dutyTime{today}c")
        is_open = _is_open(start, end, now)
        close = _close_label(end)
        # 오늘 시간표로는 닫혔어도, 어제 밤 영업이 자정을 넘겨 아직 이어지면 영업 중
        late = _late_night(item.findtext(f"dutyTime{yday}c"), now)
        if not is_open and late:
            is_open, close = True, late
        result.append({
            "id": item.findtext("hpid"),
            "name": item.findtext("dutyName"),
            "addr": item.findtext("dutyAddr"),
            "tel": item.findtext("dutyTel1"),
            "lat": item.findtext("wgs84Lat"),
            "lon": item.findtext("wgs84Lon"),
            "today_hours": _time_range(start, end),
            "is_open": is_open,
            "close_label": close,
        })
    if open_now:
        result = [p for p in result if p["is_open"]]
    # API는 시/군/구를 부분 일치로 찾아요: 부산 "서구"에 "강서구"가, 인천 "동구"에 "남동구"가 섞여요
    if sigungu:
        result = [p for p in result if p["addr"].split()[1] == sigungu]
    if name:
        # 문 연 곳이 위로 (False=0이 앞). 안정 정렬이라 같은 그룹 안은 이름순 그대로
        result.sort(key=lambda p: not p["is_open"])
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

    today, now = _now()

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

    # 새벽에만: 오늘 시간표로 닫힌 약국의 어제 시간표를 물어봐서 자정 넘김 영업을 찾아요
    # (한 곳씩 물어야 해서, 8곳씩 동시에 물어봐요. 낮에는 이 일을 안 해서 느려지지 않아요)
    if now < EARLY:
        closed = [p for p in result if not p["is_open"]]
        yday = _yesterday(today)
        with ThreadPoolExecutor(max_workers=8) as pool:
            ends = list(pool.map(lambda p: _yesterday_end(p["id"], yday), closed))
        for p, y_end in zip(closed, ends):
            late = _late_night(y_end, now)
            if late:
                p["is_open"], p["close_label"] = True, late

    if open_now:
        result = [p for p in result if p["is_open"]]
    return result[:size]
