from typing import Literal

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from ..deps import get_current_user, require_health_consent
from ..services.bag_scan import BadImage, decode_image, match_names, read_names
from ..services.dur_api import check_interaction, ingredient_names, profile_cautions
from ..services.my_meds import add_med, delete_med, get_profile, list_meds, set_profile
from ..services.safety import CAUTION_MESSAGES

router = APIRouter(
    prefix="/api/my-meds",
    tags=["MyMeds"]
)

API_DOWN = "약 정보 서버가 응답하지 않아요. 잠시 후 다시 시도해 주세요."


class MedRequest(BaseModel):
    item_seq: str = Field(min_length=1, max_length=20)
    item_name: str = Field(min_length=1, max_length=200)
    added_by: Literal["검색", "사진"] = "검색"


class ProfileRequest(BaseModel):
    target: Literal["없음", "임부", "수유", "소아", "노인"]   # 수유: AI 질문의 '먹는 사람'과 같게 (11/12)


class ScanRequest(BaseModel):
    image: str = Field(min_length=1, max_length=12_000_000)  # base64 사진 (8MB 사진이 약 11MB 글자)


@router.get("")
def my_meds(user: dict = Depends(require_health_consent)):
    return list_meds(user["user_id"])


@router.get("/ingredients")
def my_med_ingredients(user: dict = Depends(require_health_consent)):
    meds = list_meds(user["user_id"])
    return ingredient_names([med["item_seq"] for med in meds])


@router.get("/profile")
def my_profile(user: dict = Depends(require_health_consent)):
    return {"target": get_profile(user["user_id"])}


@router.put("/profile")
def change_profile(data: ProfileRequest, user: dict = Depends(require_health_consent)):
    set_profile(user["user_id"], data.target)
    return {"target": data.target}


@router.get("/cautions")
def my_med_cautions(user: dict = Depends(require_health_consent)):
    target = get_profile(user["user_id"])
    if target not in ("임부", "소아", "노인"):  # 표에는 수유도 있지만 화면에서 고를 수 없다
        return {"target": target, "results": []}
    meds = list_meds(user["user_id"])
    cautions = profile_cautions(target, [med["item_seq"] for med in meds])
    return {
        "target": target,
        "notice": CAUTION_MESSAGES[target],
        "results": [
            {"item_seq": med["item_seq"], "item_name": med["item_name"], "cautions": cautions[med["item_seq"]]}
            for med in meds
        ],
    }


@router.get("/check")
def check_my_meds(user: dict = Depends(require_health_consent)):
    meds = list_meds(user["user_id"])
    names = {med["item_seq"]: med["item_name"] for med in meds}
    try:
        # 어린이의 양은 나이와 몸무게로 정하므로 성인 최대 용량을 보여 주지 않는다
        results = check_interaction(list(names), show_max_dose=get_profile(user["user_id"]) != "소아")
    except httpx.HTTPError:
        raise HTTPException(status_code=503, detail=API_DOWN)
    for result in results:
        result["item_name_a"] = names[result["item_seq_a"]]
        result["item_name_b"] = names[result["item_seq_b"]]
    return {"level": results[0]["level"] if results else None, "results": results}


@router.post("/scan")
def scan_bag_photo(data: ScanRequest, user: dict = Depends(require_health_consent)):
    """약봉지 사진에서 약 이름을 읽고 허가정보 후보를 돌려준다. 내 약에 넣지는 않는다 (사용자가 골라서 넣는다)."""
    try:
        image = decode_image(data.image)
    except BadImage as error:
        raise HTTPException(status_code=400, detail=str(error))
    try:
        names = read_names(image)
    except httpx.HTTPStatusError as error:
        if error.response.status_code == 400:  # 사진이 커서 AI가 한 번에 받을 수 있는 양을 넘었다 (화면은 줄여서 보낸다)
            raise HTTPException(status_code=400, detail="사진이 너무 커서 읽지 못했어요. 약 이름 부분만 가까이 찍어 주세요.")
        raise HTTPException(status_code=503, detail="사진을 읽는 AI가 응답하지 않아요. 잠시 후 다시 시도해 주세요.")
    except httpx.HTTPError:
        raise HTTPException(status_code=503, detail="사진을 읽는 AI가 응답하지 않아요. 잠시 후 다시 시도해 주세요.")
    try:
        results = match_names(names)
    except httpx.HTTPError:
        raise HTTPException(status_code=503, detail=API_DOWN)
    return {"results": results}


@router.post("", status_code=201)
def register_med(data: MedRequest, user: dict = Depends(require_health_consent)):
    med = add_med(user["user_id"], data.item_seq, data.item_name, data.added_by)
    if med is None:
        raise HTTPException(status_code=409, detail="이미 등록한 약이에요.")
    return med


@router.delete("/{med_id}", status_code=204)
def remove_med(med_id: int, user: dict = Depends(get_current_user)):
    if not delete_med(user["user_id"], med_id):
        raise HTTPException(status_code=404, detail="등록된 약을 찾을 수 없어요.")
