from functools import lru_cache
from itertools import combinations
import re
import httpx
from concurrent.futures import ThreadPoolExecutor
from ..config import DATA_GO_KR_KEY
from .drug_api import get_by_seq

INGR_URL = "https://apis.data.go.kr/1471000/DrugPrdtPrmsnInfoService08/getDrugPrdtMcpnDtlInq08"
DUR_URL = "https://apis.data.go.kr/1471000/DURPrdlstInfoService03/getUsjntTabooInfoList03"
EFFECT_URL = "https://apis.data.go.kr/1471000/DURPrdlstInfoService03/getEfcyDplctInfoList03"
DUR_BASE = "https://apis.data.go.kr/1471000/DURPrdlstInfoService03/"
# 복용자 프로필별 DUR 주의 자료
CAUTION_URLS = {
    "임부": DUR_BASE + "getPwnmTabooInfoList03",
    "소아": DUR_BASE + "getSpcifyAgrdeTabooInfoList03",
    "노인": DUR_BASE + "getOdsnAtentInfoList03",
}
LEVEL_ORDER = ("block", "warn", "unknown", "pass")  # 위험한 판정부터
TIMEOUT = 15
RETRIES = 2  # 공공 API는 같은 요청도 가끔 느려서 한 번 더 시도한다

# 같은 성분도 제형에 따라 코드와 이름이 달라서, 비교할 때 이 표현을 뺀다 (예: 아세트아미노펜과립)
FORM_WORDS = re.compile(r"\(.*?\)|장용과립|장용|과립|미분화|수화물|\s")
NSAID_GROUP = "비스테로이드성 소염제"
# DUR 효능군 자료에 없는 약도 있어서, 일반의약품에 흔한 소염진통제 성분은 직접 적는다
NSAID_NAMES = {"이부프로펜", "덱시부프로펜", "나프록센", "아스피린", "케토프로펜", "록소프로펜나트륨"}
# 종합감기약 속 항히스타민제는 DUR 효능군 자료에 없어서 직접 적는다 (판피린티정의 클로르페니라민)
# 성분 이름 뒤에 염(말레산염, 염산염)이 붙으므로 이름이 들어 있는지로 본다
ANTIHISTAMINE_GROUP = "항히스타민제"  # DUR 효능군 자료와 같은 이름 (지르텍정, 알레그라정)
ANTIHISTAMINE_NAMES = (
    "클로르페니라민", "트리프롤리딘", "디펜히드라민", "독실아민", "브롬페니라민", "카르비녹사민",
    "시프로헵타딘", "히드록시진", "메퀴타진", "케토티펜",
    "세티리진", "로라타딘", "펙소페나딘", "에바스틴", "에피나스틴", "빌라스틴", "루파타딘",
)
ACETAMINOPHEN = "아세트아미노펜"
# 숫자를 코드에 정해 두지 않고, e약은요 원문에 이 문구가 있을 때만 안내한다
ACETAMINOPHEN_MAX = re.compile(r"일일\s*최대\s*용량\s*\(4,000\s*mg\)")
ACETAMINOPHEN_NOTE = (
    "식약처 e약은요 원문의 아세트아미노펜 일일 최대 용량은 4,000 mg입니다. 함께 먹으면 넘을 수 있습니다. "
    "술을 자주 마시거나 간 질환이 있으면 약사와 먼저 상의하세요"
)

def _call(url, params):
    params = {"serviceKey": DATA_GO_KR_KEY, "type": "json", "numOfRows": 100, **params}
    for attempt in range(RETRIES):
        try:
            res = httpx.get(url, params=params, timeout=TIMEOUT)
            res.raise_for_status()
            return res.json()["body"].get("items") or []
        except httpx.HTTPError:
            if attempt == RETRIES - 1:
                raise

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
    # 사유가 비어 있어도 금기는 금기이므로 빈 값으로 두지 않는다
    return {item["MIXTURE_ITEM_SEQ"]: (item["PROHBT_CONTENT"] or "사유 정보 없음").strip() for item in items}

@lru_cache(maxsize=1000)
def get_effect_groups(item_seq):
    items = _call(EFFECT_URL, {"itemSeq": item_seq})
    return frozenset(item["SERS_NAME"] for item in items if item.get("SERS_NAME"))

@lru_cache(maxsize=1000)
def _states_max_dose(item_seq):
    """성인용 약의 e약은요 경고문에 아세트아미노펜 최대 용량이 적혀 있는지 본다. 어린이 약의 양은 나이와 몸무게로 정한다."""
    drug = get_by_seq(item_seq)
    if drug is None or "어린이" in drug["item_name"]:
        return False
    return bool(ACETAMINOPHEN_MAX.search(drug.get("atpn_warn") or ""))

def _clean_name(name):
    return FORM_WORDS.sub("", name).lower()

def _same_ingredients(ingr_a, ingr_b):
    """두 약에 모두 든 성분의 이름. 코드가 같거나, 제형 표현을 뺀 이름이 같으면 같은 성분으로 본다."""
    codes_b = {i["MTRAL_CODE"] for i in ingr_b}
    names_b = {_clean_name(i["MTRAL_NM"]) for i in ingr_b}
    return sorted({
        _clean_name(i["MTRAL_NM"]) for i in ingr_a
        if i["MTRAL_CODE"] in codes_b or _clean_name(i["MTRAL_NM"]) in names_b
    })

def _groups(effects, ingredients):
    groups = set(effects or ())
    names = [_clean_name(i["MTRAL_NM"]) for i in ingredients or []]
    if any(name in NSAID_NAMES for name in names):
        groups.add(NSAID_GROUP)
    if any(part in name for name in names for part in ANTIHISTAMINE_NAMES):  # 세티리진염산염 -> 세티리진
        groups.add(ANTIHISTAMINE_GROUP)
    return groups

def _judge(seq_a, seq_b, a, b, show_max_dose=True):
    """조회한 자료로 판정한다. a, b는 (금기, 성분, 효능군)이고 조회에 실패한 자료는 None이다."""
    taboo_a, ingr_a, effects_a = a
    taboo_b, ingr_b, effects_b = b
    reasons = []
    basis = []  # 판정에 쓴 자료
    failed = None in (*a, *b)

    # 1) 병용금기
    taboo = (taboo_a or {}).get(seq_b) or (taboo_b or {}).get(seq_a)
    if taboo:
        reasons.append(f"함께 먹으면 안 되는 약입니다 (병용금기: {taboo})")
        basis.append("식약처 DUR 병용금기")

    # 2) 같은 성분 겹침
    same = _same_ingredients(ingr_a or [], ingr_b or [])
    for name in same:
        reasons.append(f"{name} 성분이 두 약에 모두 들어 있어 너무 많이 먹게 될 수 있습니다")
    if same:
        basis.append("식약처 의약품 허가정보 성분 비교")
    if show_max_dose and ACETAMINOPHEN in same and all(_lookup_or_none(_states_max_dose, seq) for seq in (seq_a, seq_b)):
        reasons.append(ACETAMINOPHEN_NOTE)
        basis.append("식약처 e약은요 경고문")

    # 3) 같은 계열 겹침. 같은 성분이 있으면 이미 알렸으므로 다시 말하지 않는다
    same_group = [] if same else sorted(_groups(effects_a, ingr_a) & _groups(effects_b, ingr_b))
    for group in same_group:
        reasons.append(f"{group} 계열 약이 겹쳐 효과와 부작용이 함께 커질 수 있습니다")
    if same_group:
        basis.append("식약처 DUR 효능군 · 서비스 소염진통제·항히스타민제 목록")

    if taboo:
        level = "block"
    elif same or same_group:
        level = "warn"
    elif failed or not ingr_a or not ingr_b:
        # 성분을 못 찾으면 겹치는지 알 수 없으므로 pass라고 답하지 않는다
        level = "unknown"
    else:
        level = "pass"

    if failed:
        reasons.append("약 정보 서버가 응답하지 않아 일부를 확인하지 못했습니다")
    elif level == "unknown":
        reasons.append("약의 성분 정보를 찾지 못해 성분이 겹치는지 확인하지 못했습니다")
    return {"level": level, "reasons": reasons, "basis": basis}

def check_together(seq_a, seq_b):
    # 여섯 가지 조회를 한꺼번에 출발시킨다
    with ThreadPoolExecutor(max_workers=6) as pool:
        a = [pool.submit(lookup, seq_a) for lookup in (get_taboo_partners, get_ingredients, get_effect_groups)]
        b = [pool.submit(lookup, seq_b) for lookup in (get_taboo_partners, get_ingredients, get_effect_groups)]
    return _judge(seq_a, seq_b, [f.result() for f in a], [f.result() for f in b])

def _lookup_or_none(lookup, item_seq):
    try:
        return lookup(item_seq)
    except (httpx.HTTPError, ValueError, KeyError):  # 끊김, 시간 초과, 이상한 응답
        return None

def _lookup_all(item_seq):
    return [_lookup_or_none(lookup, item_seq) for lookup in (get_taboo_partners, get_ingredients, get_effect_groups)]

def _ingredient_names(item_seq):
    items = _lookup_or_none(get_ingredients, item_seq)
    if items is None:
        return None
    return list(dict.fromkeys(_clean_name(item["MTRAL_NM"]) for item in items))

def ingredient_names(item_seqs):
    """약마다 성분 이름 목록을 돌려준다. 조회에 실패한 약은 None, 성분 정보가 없는 약은 빈 목록."""
    seqs = list(dict.fromkeys(item_seqs))
    with ThreadPoolExecutor(max_workers=4) as pool:
        return dict(zip(seqs, pool.map(_ingredient_names, seqs)))

@lru_cache(maxsize=1000)
def _get_cautions(target, item_seq):
    rows = []
    for item in _call(CAUTION_URLS[target], {"itemSeq": item_seq}):
        # 내용이 비어 있거나 "-"인 자료도 있어서, 그때는 내용 없이 종류와 성분만 보여 준다
        content = (item.get("PROHBT_CONTENT") or "").strip(' "-')
        row = {"type": item.get("TYPE_NAME") or target, "ingredient": item.get("INGR_NAME") or "", "content": content}
        if row not in rows:
            rows.append(row)
    return tuple(rows)

def _cautions_or_none(target, item_seq):
    try:
        return list(_get_cautions(target, item_seq))
    except (httpx.HTTPError, ValueError, KeyError):
        return None

def profile_cautions(target, item_seqs):
    """약마다 프로필의 DUR 주의 자료를 돌려준다. 조회에 실패한 약은 None, 자료가 없는 약은 빈 목록."""
    seqs = list(dict.fromkeys(item_seqs))
    with ThreadPoolExecutor(max_workers=4) as pool:
        return dict(zip(seqs, pool.map(lambda seq: _cautions_or_none(target, seq), seqs)))

def check_interaction(item_seqs, show_max_dose=True):
    """약 여러 개를 두 개씩 모두 비교한다. 위험한 판정이 앞에 오는 목록을 돌려준다.

    약마다 한 번만 조회하고, 일부가 실패해도 나머지 결과는 돌려준다.
    """
    seqs = list(dict.fromkeys(item_seqs))  # 같은 약은 한 번만
    with ThreadPoolExecutor(max_workers=4) as pool:
        lookups = dict(zip(seqs, pool.map(_lookup_all, seqs)))
    results = [
        {"item_seq_a": a, "item_seq_b": b, **_judge(a, b, lookups[a], lookups[b], show_max_dose)}
        for a, b in combinations(seqs, 2)
    ]
    results.sort(key=lambda result: LEVEL_ORDER.index(result["level"]))
    return results
