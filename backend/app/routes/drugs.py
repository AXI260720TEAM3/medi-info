import httpx
from fastapi import APIRouter, HTTPException
from ..services.drug_api import search_by_name, get_by_seq, search_by_efcy
from ..services.query_ai import parse_query

router = APIRouter(
    prefix="/api",
    tags=["Drugs"]
)

API_DOWN = "약 정보 서버가 응답하지 않아요. 잠시 후 다시 시도해 주세요."
AI_DOWN = "AI 서버가 응답하지 않아요. 잠시 후 다시 시도해 주세요."


@router.get("/drugs")
def drug_list(q: str, page: int = 1): 
    try:
        total, items = search_by_name(q, page=page)
    except httpx.HTTPError:
        raise HTTPException(status_code=503, detail=API_DOWN)
    return {"total":total, "page": page, "items": items}

@router.get("/drugs/smart")
def drug_smart(text: str, page: int = 1):
    try:
        parsed = parse_query(text)
    except httpx.HTTPError:
        raise HTTPException(status_code=503, detail=AI_DOWN)

    try:
        if parsed["drug_name"]:
            total, items = search_by_name(parsed["drug_name"], page=page)
        elif parsed["symptom"]:
            total, items = search_by_efcy(parsed["symptom"], page=page)
        else:
            total, items = 0, []
    except httpx.HTTPError:
        raise HTTPException(status_code=503, detail=API_DOWN)

    return {"parsed": parsed, "total": total, "page": page, "items": items}

@router.get("/drugs/{item_seq}")
def drug_detail(item_seq: str):
    try:
        drug = get_by_seq(item_seq)
    except httpx.HTTPError:
        raise HTTPException(status_code=503, detail=API_DOWN)
    if drug is None:
        raise HTTPException(status_code=404, detail="그 약을 찾을 수 없어요.")
    return drug

