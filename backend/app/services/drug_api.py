import httpx
from ..config import DATA_GO_KR_KEY
from .api_cache import ttl_cache

URL = "https://apis.data.go.kr/1471000/DrbEasyDrugInfoService/getDrbEasyDrugList"
CACHE_SECONDS = 3600   # 같은 질문은 1시간 동안 기억 (약 정보는 하루에도 거의 안 바뀌어요)
TIMEOUT = 8            # 한 번에 8초까지 기다리고, 연결·시간 초과면 한 번 더 (최악 16초)

# API 칸 이름 -> 우리 칸 이름
FIELDS = {
    "itemSeq": "item_seq",
    "itemName": "item_name",
    "entpName": "entp_name",
    "efcyQesitm": "efcy",
    "useMethodQesitm": "use_method",
    "atpnWarnQesitm": "atpn_warn",
    "atpnQesitm": "atpn",
    "intrcQesitm": "intrc",
    "seQesitm": "se",
    "depositMethodQesitm": "deposit",
    "itemImage": "item_image",
    "updateDe": "update_de",
}

def _call(params):
    params = {"serviceKey": DATA_GO_KR_KEY, "type":"json", **params}
    # e약은요가 가끔 10초 가까이 걸리거나 끊겨요. 연결·시간 초과면 한 번만 더 해 봐요
    for attempt in (1, 2):
        try:
            res = httpx.get(URL, params=params, timeout=TIMEOUT)
            break
        except (httpx.TimeoutException, httpx.ConnectError):
            if attempt == 2:
                raise
    res.raise_for_status()
    body = res.json()["body"]
    items = body.get("items") or []
    return body["totalCount"], [_rename(item) for item in items]

def _rename(item):
    return {ours: item.get(api) for api, ours in FIELDS.items()}

@ttl_cache(CACHE_SECONDS)
def search_by_name(name, page=1, size=10):
    return _call({"itemName": name, "pageNo": page, "numOfRows": size})

@ttl_cache(CACHE_SECONDS)
def get_by_seq(item_seq):
    total, items = _call({"itemSeq": item_seq})
    for item in items:
        if item["item_seq"] == item_seq:
            return item
    return None

@ttl_cache(CACHE_SECONDS)
def search_by_company(company, page=1, size=10):
    """e약은요를 회사 이름으로 찾기 (부분 일치: '동아제약' → '동아제약(주)')"""
    return _call({"entpName": company, "pageNo": page, "numOfRows": size})


@ttl_cache(CACHE_SECONDS)
def search_by_efcy(symptom, page=1, size=10):
    return _call({"efcyQesitm": symptom, "pageNo":page, "numOfRows": size})


def _rank(item_name, name):
    """이름이 검색어로 시작하는 약 먼저, 그다음 이름이 짧은 약 먼저"""
    base = item_name.split("(")[0].strip()
    return (not base.startswith(name), len(base), item_name)

def search_by_name_ranked(name, page=1, size=10):
    """이름 검색 결과를 정렬해서 한 쪽만 돌려준다. 100건이 넘으면 e약은요 순서 그대로."""
    total, items = search_by_name(name, page=1, size=100)
    if total > 100:
        return search_by_name(name, page=page, size=size)
    items.sort(key=lambda d: _rank(d["item_name"], name))
    start = (page - 1) * size
    return total, items[start:start + size]