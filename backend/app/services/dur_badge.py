import httpx

from ..config import DATA_GO_KR_KEY
from .api_cache import ttl_cache

# 약 하나의 DUR 종류를 배지로 (기능명세 A-5). 검색 결과·약 상세에 "임부 금기", "용량 주의" 같은 배지
# DUR품목정보(종합) API는 약 하나에 해당하는 DUR 종류를 쉼표로 한 번에 줘요: "임부금기,용량주의,첨가제주의"
# (③의 dur_api.py는 종류마다 따로 부르는 상세 자료용이고, 배지는 종류 이름만 있으면 돼서 이 API 하나로 충분해요)
URL = "https://apis.data.go.kr/1471000/DURPrdlstInfoService03/getDurPrdlstInfoList03"
TIMEOUT = 8

# DUR 종류 이름 → 화면에 보여 줄 글자와 배지 색. 여기 없는 종류는 배지로 보여 주지 않아요
#   taboo = 금기(빨강): 그 대상에게는 쓰면 안 됨 / caution = 주의(주황): 쓸 때 조심
BADGES = {
    "병용금기": ("함께 먹기 금기", "taboo"),
    "특정연령대금기": ("연령 금기", "taboo"),
    "임부금기": ("임부 금기", "taboo"),
    "용량주의": ("용량 주의", "caution"),
    "투여기간주의": ("투여 기간 주의", "caution"),
    "노인주의": ("노인 주의", "caution"),
    "효능군중복": ("효능군 중복 주의", "caution"),
    "분할주의": ("쪼개지 않기", "caution"),
    "서방정분할주의": ("쪼개지 않기", "caution"),
}


@ttl_cache(6 * 3600)   # DUR 자료는 자주 안 바뀌어서 6시간 기억
def dur_types(item_seq):
    """약 하나에 해당하는 DUR 종류 이름 목록. DUR 자료가 없는 약은 빈 목록"""
    params = {"serviceKey": DATA_GO_KR_KEY, "type": "json", "numOfRows": 5, "itemSeq": item_seq}
    for attempt in (1, 2):
        try:
            res = httpx.get(URL, params=params, timeout=TIMEOUT)
            break
        except (httpx.TimeoutException, httpx.ConnectError):
            if attempt == 2:
                raise
    res.raise_for_status()
    items = res.json()["body"].get("items") or []
    if not items:
        return []
    item = {k.strip(): v for k, v in items[0].items()}   # 이 API는 칸 이름 뒤에 공백이 붙어 와요 ('TYPE_NAME  ')
    return [name.strip() for name in (item.get("TYPE_NAME") or "").split(",") if name.strip()]


def to_badges(types):
    """DUR 종류 이름 목록 → 화면 배지 목록 [{"label": "임부 금기", "type": "taboo"}, ...]
    BADGES에 있는 종류만, 금기(taboo)를 주의(caution)보다 앞에, 같은 글자는 한 번만"""
    badges = []
    seen = set()

    for name in types:
        found = BADGES.get(name)
        if found is None:
            continue
        label, kind = found
        if label in seen:
            continue
        seen.add(label)
        badges.append({"label": label, "type": kind})
    return sorted(badges, key=lambda b: b["type"] != "taboo")   # 금기(False=0)가 주의(True=1)보다 앞
