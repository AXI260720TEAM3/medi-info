from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from ..deps import get_current_user
from ..services.my_meds import add_med, delete_med, list_meds

router = APIRouter(
    prefix="/api/my-meds",
    tags=["MyMeds"]
)


class MedRequest(BaseModel):
    item_seq: str = Field(min_length=1, max_length=20)
    item_name: str = Field(min_length=1, max_length=200)


@router.get("")
def my_meds(user: dict = Depends(get_current_user)):
    return list_meds(user["user_id"])


@router.post("", status_code=201)
def register_med(data: MedRequest, user: dict = Depends(get_current_user)):
    med = add_med(user["user_id"], data.item_seq, data.item_name)
    if med is None:
        raise HTTPException(status_code=409, detail="이미 등록한 약이에요.")
    return med


@router.delete("/{med_id}", status_code=204)
def remove_med(med_id: int, user: dict = Depends(get_current_user)):
    if not delete_med(user["user_id"], med_id):
        raise HTTPException(status_code=404, detail="등록된 약을 찾을 수 없어요.")
