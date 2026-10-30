from functools import lru_cache
import httpx
from concurrent.futures import ThreadPoolExecutor
from ..config import DATA_GO_KR_KEY
from .drug_api import get_by_seq

INGR_URL = "https://apis.data.go.kr/1471000/DrugPrdtPrmsnInfoService08/getDrugPrdtMcpnDtlInq08"
DUR_URL = "https://apis.data.go.kr/1471000/DURPrdlstInfoService03/getUsjntTabooInfoList03"

def _call(url, params):
    params = {"serviceKey": DATA_GO_KR_KEY, "type": "json", "numOfRows": 100, **params}
    res = httpx.get(url, params=params, timeout=10)
    res.raise_for_status()
    return res.json()["body"].get("items") or []

@lru_cache(maxsize=1000)
def get_ingredients(item_seq):
    drug = get_by_seq(item_seq)
    if drug is None:
        return []
    items = _call(INGR_URL, {"Prduct": drug["item_name"]})
    return [item for item in items if item["ITEM_SEQ"] == item_seq]

@lru_cache(maxsize=1000)
def get_taboo_partners(item_seq):
    items = _call(DUR_URL, {"itemSeq": item_seq, "numOfRows": 500})
    return {item["MIXTURE_ITEM_SEQ"]: item["PROHBT_CONTENT"].strip() for item in items}

def check_together(seq_a, seq_b):
    reasons = []

    # 네 가지 조회를 한꺼번에 출발시킨다
    with ThreadPoolExecutor(max_workers=4) as pool:
        taboo_a = pool.submit(get_taboo_partners, seq_a)
        taboo_b = pool.submit(get_taboo_partners, seq_b)
        ingr_a = pool.submit(get_ingredients, seq_a)
        ingr_b = pool.submit(get_ingredients, seq_b)

    # 1) 병용금기
    taboo = taboo_a.result().get(seq_b) or taboo_b.result().get(seq_a)
    if taboo:
        reasons.append(f"함께 먹으면 안 되는 약입니다 (병용금기: {taboo})")

    # 2) 같은 성분 겹침
    ingr_a = {i["MTRAL_CODE"]: i["MTRAL_NM"] for i in ingr_a.result()}
    ingr_b = {i["MTRAL_CODE"]: i["MTRAL_NM"] for i in ingr_b.result()}
    for code in ingr_a.keys() & ingr_b.keys():
        reasons.append(f"{ingr_a[code]} 성분이 두 약에 모두 들어 있어 너무 많이 먹게 될 수 있습니다")

    if taboo:
        level = "block"
    elif reasons:
        level = "warn"
    else:
        level = "pass"
    return {"level": level, "reasons": reasons}
