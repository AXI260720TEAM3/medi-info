import httpx
from fastapi import APIRouter, HTTPException, Query
from ..services.pharmacy_api import search_nearby, search_pharmacy

router = APIRouter(
    prefix="/api",
    tags=["Pharmacy"]
)

API_DOWN = "약국 정보 서버가 응답하지 않아요. 잠시 후 다시 시도해 주세요."
PAGE_SIZE = 10


@router.get("/pharmacies")
def pharmacy_list(sido: str, sigungu: str = "", page: int = Query(1, ge=1), open_now: bool = True):
    try:
        total,items = search_pharmacy(sido, sigungu, page=page, size=PAGE_SIZE, open_now=open_now)
    except httpx.HTTPError:
        raise HTTPException(status_code=503, detail=API_DOWN)
    return {"total": total, "page": page, "size": PAGE_SIZE, "items":items}


# 한국 땅 범위(대략)만 받아요. 범위 밖이면 FastAPI가 422로 막아요
@router.get("/pharmacies/near")
def pharmacy_near(lat: float = Query(..., ge=33, le=39), lon: float = Query(..., ge=124, le=132), open_now: bool = True):
    try:
        items = search_nearby(lat, lon, size=PAGE_SIZE, open_now=open_now)
    except httpx.HTTPError:
        raise HTTPException(status_code=503, detail=API_DOWN)
    # 지역 검색과 같은 모양으로 돌려줘서 화면이 한 가지 모양만 다루게
    return {"total": len(items), "page": 1, "size": PAGE_SIZE, "items": items}

