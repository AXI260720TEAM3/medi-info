import re

from .drug_api import search_by_name
from .query_ai import parse_query
from .synonym import fix_drug_typo


def base_name(item_name):
    """'게보린정(수출명:돌도린정)' -> '게보린정'"""
    return item_name.split("(")[0].strip()

def name_variants(name):
    """못 찾았을 떄 다시 찾아 볼 이름들. 첫 번째는 항상 원래 이름."""
    variants = [name, name.replace(" ", ""), name.replace("밀리그램", "밀리그람")]
    first = re.match(r"[가-힣]+", name)
    if first:
        variants.append(first.group())
    return list(dict.fromkeys(variants))

def find_drug(question):
    parsed = parse_query(question)
    name = parsed["drug_name"]
    if not name:
        # 약 이름이 없어도 AI가 뽑은 성분·증상은 돌려줘요. AI 질문이 되묻기 전에 써요 (11/12, routes/chat.py)
        return {"status": "none", "parsed": parsed}

    variants = name_variants(name)
    fixed = fix_drug_typo(name)
    if fixed != name:
        variants = list(dict.fromkeys(variants + name_variants(fixed)))

    for i, variant in enumerate(variants):
        total, items = search_by_name(variant, size=20)
        if total == 0:
            continue

        # 원래 이름으로 찾았을 때만 확정한다
        if i == 0:
            if total == 1:
                return {"status": "found","drug": items[0]}
            exact = [d for d in items if base_name(d["item_name"]) == name]
            if len(exact) == 1:
                return {"status": "found", "drug": exact[0]}

        # 후보가 여럿이거나 이름을 고쳐 찾았으면 사용자가 고른다
        return {"status" : "ambiguous", "name": name, "candidates": items}
    return {"status":"none", "name":name}