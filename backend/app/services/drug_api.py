import httpx
from ..config import DATA_GO_KR_KEY

URL = "https://apis.data.go.kr/1471000/DrbEasyDrugInfoService/getDrbEasyDrugList"

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
    res = httpx.get(URL, params=params, timeout=10)
    res.raise_for_status()
    body = res.json()["body"]
    items = body.get("items") or []
    return body["totalCount"], [_rename(item) for item in items]

def _rename(item):
    return {ours: item.get(api) for api, ours in FIELDS.items()}

def search_by_name(name, page=1, size=10):
    return _call({"itemName": name, "pageNo": page, "numOfRows": size})

def get_by_seq(item_seq):
    total, items = _call({"itemSeq": item_seq})
    for item in items:
        if item["item_seq"] == item_seq:
            return item
    return None

def search_by_efcy(symptom, page=1, size=10):
    return _call({"efcyQesitm": symptom, "pageNo":page, "numOfRows": size})
