import httpx
from ..config import DATA_GO_KR_KEY

URL = "https://apis.data.go.kr/1471000/DrugPrdtPrmsnInfoService08/getDrugPrdtPrmsnInq08"

# 허가정보 칸 이름(대문자) -> 우리 이름
FIELDS = {
    "ITEM_SEQ": "item_seq",
    "ITEM_NAME": "item_name",
    "ENTP_NAME": "entp_name",
    "SPCLTY_PBLC": "etc_otc",
}

def _rename(item):
    return {ours: item.get(api) for api, ours in FIELDS.items()}

def search_permit(name):
    params = {"serviceKey": DATA_GO_KR_KEY, "type":"json", "item_name":name, "numOfRows":100}
    res = httpx.get(URL, params=params, timeout=10)
    res.raise_for_status()
    items = res.json()["body"].get("items") or []

    result = []
    # 취소된 약, 수출용 약은 뺀다
    for item in items:
        if item.get("CANCEL_NAME") == "정상" and "(수출용)" not in item.get("ITEM_NAME",""):
            result.append(_rename(item))
    return result

