import logging
from functools import lru_cache

import httpx
from fastapi import APIRouter, HTTPException, Query
from ..services.drug_api import get_by_seq, search_by_efcy
from ..services.drug_search import search_by_company, search_by_ingredient, search_merged
from ..services.permit_api import get_permit_detail
from ..services.dur_api import get_ingredients
from ..services.dur_badge import dur_types, to_badges
from ..services.query_ai import parse_query
from ..services.synonym import find_symptom

router = APIRouter(
    prefix="/api",
    tags=["Drugs"]
)

API_DOWN = "약 정보 서버가 응답하지 않아요. 잠시 후 다시 시도해 주세요."
AI_DOWN = "AI 서버가 응답하지 않아요. 잠시 후 다시 시도해 주세요."
PAGE_SIZE = 10


# 같은 질문은 AI에게 한 번만 묻는다 (쪽을 넘겨도 같은 검색어를 쓰게)
@lru_cache(maxsize=256)
def cached_parse(text):
    return parse_query(text)

@router.get("/drugs")
def drug_list(q: str, page: int= Query(1, ge=1)): 
    try:
        total, items = search_merged(q, page=page, size=PAGE_SIZE)
    except httpx.HTTPError:
        raise HTTPException(status_code=503, detail=API_DOWN)
    return {"total": total, "page": page, "size": PAGE_SIZE, "items": items}

@router.get("/drugs/smart")
def drug_smart(text: str, page: int = Query(1, ge=1)):
    try:
        parsed = dict(cached_parse(text))
    except (httpx.HTTPError, ValueError, KeyError):
        # AI가 검색어를 못 만들어도 503으로 끝내지 않고, 증상 사전 → 이름 검색으로 이어서 찾아요 (11/13)
        # 예: "콧물이 나요" → qwen이 '콧물'을 한자로 쓰려다 같은 글자를 되풀이해 Ollama가 멈춤
        #     ("prediction aborted, token repeat limit reached", 500) → 화면에 "AI 서버가 응답하지 않아요"
        logging.warning("약 찾기 AI 검색어 변환 실패 → 사전·이름 검색으로: %r", text)
        symptom = find_symptom(text)
        parsed = {"drug_name": None if symptom else text.strip(), "ingredient": None, "company": None,
                  "symptom": symptom, "ai_failed": True}
    parsed["symptom"] = find_symptom(text) or parsed["symptom"]

    try:
        if parsed["drug_name"]:
            total, items = search_merged(parsed["drug_name"], page=page, size=PAGE_SIZE)
        elif parsed["ingredient"]:
            total, items, parsed["ingredient_en"], parsed["ingredient_all"] = search_by_ingredient(parsed["ingredient"], page=page, size=PAGE_SIZE)
        elif parsed["company"]:
            total, items = search_by_company(parsed["company"], page=page, size=PAGE_SIZE)
        elif parsed["symptom"]:
            total, items = search_by_efcy(parsed["symptom"], page=page, size=PAGE_SIZE)
        else:
            total, items = 0, []
    except httpx.HTTPError:
        raise HTTPException(status_code=503, detail=API_DOWN)

    return {"parsed": parsed, "total": total, "page": page, "size": PAGE_SIZE ,"items": items}

@router.get("/drugs/{item_seq}/ingredients")
def drug_ingredients(item_seq: str):
    """약 상세의 성분 목록. 허가정보 API라서 상세와 따로 불러요."""
    try:
        items = get_ingredients(item_seq)
    except httpx.HTTPError:
        raise HTTPException(status_code=503, detail=API_DOWN)
    names = [item["MTRAL_NM"] for item in items if item.get("MTRAL_NM")]
    return {"ingredients": list(dict.fromkeys(names))}

@router.get("/drugs/{item_seq}/dur")
def drug_dur(item_seq: str):
    """약 하나의 DUR 배지 (A-5). 검색 카드·상세가 화면을 먼저 그린 뒤 따로 불러요.
    공공 API가 안 되면 오류 대신 badges=None → 화면은 배지 없이 그대로"""
    try:
        return {"badges": to_badges(dur_types(item_seq))}
    except (httpx.HTTPError, ValueError, KeyError):
        return {"badges": None}

@router.get("/drugs/{item_seq}")
def drug_detail(item_seq: str):
    try:
        drug = get_by_seq(item_seq)
        if drug is None:
            drug = get_permit_detail(item_seq)
    except httpx.HTTPError:
        raise HTTPException(status_code=503, detail=API_DOWN)
    if drug is None:
        raise HTTPException(status_code=404, detail="그 약을 찾을 수 없어요.") # 둘 다 없으면 404
    return drug


