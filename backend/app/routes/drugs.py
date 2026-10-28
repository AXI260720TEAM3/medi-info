import httpx
from fastapi import APIRouter, HTTPException
from ..services.drug_api import search_by_name, get_by_seq

router = APIRouter(
    prefix="/api",
    tags=["Drugs"]
)

API_DOWN = "약 정보 서버가 응답하지 않아요. 잠시 후 다시 시도해 주세요."


@router.get("/drugs")
def drug_list(q: str, page: int = 1): 
    try:
        total, items = search_by_name(q, page=page)
    except httpx.HTTPError:
        raise HTTPException(status_code=503, detail=API_DOWN)
    return {"total":total, "page": page, "items": items}

@router.get("/drugs/{item_seq}")
def drug_detail(item_seq: str):
    try:
        drug = get_by_seq(item_seq)
    except httpx.HTTPError:
        raise HTTPException(status_code=503, detail=API_DOWN)
    if drug is None:
        raise HTTPException(status_code=404, detail="그 약을 찾을 수 없어요.")
    return drug

