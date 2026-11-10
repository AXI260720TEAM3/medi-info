"""이름 검색: e약은요(쉬운 설명)와 허가정보(전문의약품 포함)를 품목번호로 합친다."""
import httpx

from .drug_api import search_by_name, _rank
from .permit_api import english_ingredient, search_permit, search_permit_by
from .drug_api import search_by_company as easy_by_company


def merge(easy, permit):
    """같은 품목번호는 한 개로 합친다. e약은요에 있는 약은 has_easy=True."""
    merged = {}
    # 허가정보 먼저 넣고, e약은요 내용으로 덮어 합친다
    for d in permit:
        merged[d["item_seq"]] = {**d, "has_easy": False}
    for d in easy:
        if "(수출용)" in d["item_name"]:   # 허가정보 쪽과 같은 규칙 (e약은요에도 수출용이 섞여 있어요)
            continue
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


def _page(items, page, size):
    start = (page - 1) * size
    return len(items), items[start:start + size]


def search_by_ingredient(name, page=1, size=10):
    """성분으로 찾기 (A-1). 한글이면 영어 성분 이름으로 바꿔 허가정보에서 찾아요.
    (전체 건수, 약 목록, 영어 성분 이름, 허가정보 전체 건수)를 돌려줘요. 영어 이름을 못 찾으면 0건
    허가정보는 앞 100건만 받아서, 허가정보 전체 건수가 100보다 크면 화면이 "앞 100건만" 안내를 해요"""
    english = name if name.isascii() else english_ingredient(name)
    if not english:
        return 0, [], None, 0
    permit_total, items = search_permit_by("item_ingr_name", english)
    for d in items:
        d["has_easy"] = None   # 쉬운 설명(e약은요)이 있는지 모름 → 화면에서 '쉬운 설명 없음' 배지를 달지 않아요
    items.sort(key=lambda d: d["item_name"])
    return (*_page(items, page, size), english, permit_total)


def search_by_company(name, page=1, size=10):
    """회사로 찾기 (A-1). e약은요(일반의약품)와 허가정보(전문의약품 포함)를 품목번호로 합쳐요 (이름 검색 합치기와 같은 방식)"""
    _, easy = easy_by_company(name, size=100)
    easy = [d for d in easy if "(수출용)" not in d["item_name"]]   # 허가정보 쪽과 같은 규칙 (계안겔(수출용) 같은 것)
    try:
        _, permit = search_permit_by("entp_name", name)
    except httpx.HTTPError:
        permit = []
    items = merge(easy, permit)
    items.sort(key=lambda d: d["item_name"])
    return _page(items, page, size)

