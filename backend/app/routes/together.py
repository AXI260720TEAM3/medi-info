import httpx
from fastapi import APIRouter, HTTPException
from ..services.dur_api import check_together

router = APIRouter(
    prefix="/api",
    tags=["Together"]
)

API_DOWN = "약 정보 서버가 응답하지 않아요. 잠시 후 다시 시도해 주세요."


@router.get("/together")  #FastAPI야, 이 함수를 이 주소(/api/together)에 연결해 줘
def together(a: str, b: str):
    try:
        return check_together(a, b)
    except httpx.HTTPError:
        raise HTTPException(status_code=503, detail=API_DOWN)
