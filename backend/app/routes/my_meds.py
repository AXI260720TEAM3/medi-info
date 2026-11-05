import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from ..deps import get_current_user, require_health_consent
from ..services.dur_api import check_interaction, ingredient_names
from ..services.my_meds import add_med, delete_med, list_meds

router = APIRouter(
    prefix="/api/my-meds",
    tags=["MyMeds"]
)

API_DOWN = "약 정보 서버가 응답하지 않아요. 잠시 후 다시 시도해 주세요."


class MedRequest(BaseModel):
    item_seq: str = Field(min_length=1, max_length=20)
    item_name: str = Field(min_length=1, max_length=200)


@router.get("")
def my_meds(user: dict = Depends(require_health_consent)):
    return list_meds(user["user_id"])


@router.get("/ingredients")
def my_med_ingredients(user: dict = Depends(require_health_consent)):
    meds = list_meds(user["user_id"])
    return ingredient_names([med["item_seq"] for med in meds])


@router.get("/check")
def check_my_meds(user: dict = Depends(require_health_consent)):
    meds = list_meds(user["user_id"])
    names = {med["item_seq"]: med["item_name"] for med in meds}
    try:
        results = check_interaction(list(names))
    except httpx.HTTPError:
        raise HTTPException(status_code=503, detail=API_DOWN)
    for result in results:
        result["item_name_a"] = names[result["item_seq_a"]]
        result["item_name_b"] = names[result["item_seq_b"]]
    return {"level": results[0]["level"] if results else None, "results": results}


@router.post("", status_code=201)
def register_med(data: MedRequest, user: dict = Depends(require_health_consent)):
    med = add_med(user["user_id"], data.item_seq, data.item_name)
    if med is None:
        raise HTTPException(status_code=409, detail="이미 등록한 약이에요.")
    return med


@router.delete("/{med_id}", status_code=204)
def remove_med(med_id: int, user: dict = Depends(get_current_user)):
    if not delete_med(user["user_id"], med_id):
        raise HTTPException(status_code=404, detail="등록된 약을 찾을 수 없어요.")
