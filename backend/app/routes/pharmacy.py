import httpx
from fastapi import APIRouter, HTTPException, Query
from ..services.pharmacy_api import search_pharmacy

router = APIRouter(
    prefix="/api",
    tags=["Pharmacy"]
)

API_DOWN = "약국 정보 서버가 응답하지 않아요. 잠시 후 다시 시도해 주세요."
PAGE_SIZE = 10


@router.get("/pharmacies")
def pharmacy_list(sido: str, sigungu: str, page: int = Query(1, ge=1)):
    try:
        total,items = search_pharmacy(sido, sigungu, page=page, size=PAGE_SIZE)
    except httpx.HTTPError:
        raise HTTPException(status_code=503, detail=API_DOWN)
    return {"total": total, "page": page, "size": PAGE_SIZE, "items":items}

