"""이름 검색: e약은요(쉬운 설명)와 허가정보(전문의약품 포함)를 품목번호로 합친다."""
import httpx

from .drug_api import search_by_name, _rank
from .permit_api import search_permit


def merge(easy, permit):
    """같은 품목번호는 한 개로 합친다. e약은요에 있는 약은 has_easy=True."""
    merged = {}
    # 허가정보 먼저 넣고, e약은요 내용으로 덮어 합친다
    for d in permit:
        merged[d["item_seq"]] = {**d, "has_easy": False}
    for d in easy:
        merged[d["item_seq"]] = {**merged.get(d["item_seq"], {}), **d, "has_easy": True}
    return list(merged.values())


def search_merged(name, page=1, size=10):
    _, easy = search_by_name(name, page=1, size=100)  # e약은요가 안 되면 에러 → 503
    try:
        permit = search_permit(name)
    except httpx.HTTPError:
        permit = []  # 허가정보만 안 되면 e약은요 결과라도 보여 준다
    items = merge(easy, permit)
    items.sort(key=lambda d: _rank(d["item_name"], name))
    start = (page - 1) * size
    return len(items), items[start:start + size]
