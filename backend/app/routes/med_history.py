
from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from ..deps import require_health_consent
from ..services.med_history import (
    ActiveHistoryExistsError,
    HistoryNotFoundError,
    InvalidHistoryDateError,
    MedNotRegisteredError,
    add_use_history,
    delete_use_history,
    list_use_history,
    stop_use_history,
    update_use_history,
)

router = APIRouter(
    prefix="/api/med-history",
    tags=["MedHistory"],
)


# 새로운 복용 기록을 만들 때 받는 정보
class HistoryCreateRequest(BaseModel):
    med_id: int = Field(gt=0)
    start_date: date
    times_per_day: int | None = Field(default=None, ge=1, le=24)
    duration_days: int | None = Field(default=None, ge=1)


# 기존 복용 기록을 수정할 때 받는 정보
class HistoryUpdateRequest(BaseModel):
    start_date: date
    times_per_day: int | None = Field(default=None, ge=1, le=24)
    duration_days: int | None = Field(default=None, ge=1)


# 복용을 중단할 때 받는 정보
class HistoryStopRequest(BaseModel):
    stopped_at: date


# 1. 복용이력 조회
@router.get("")
def get_histories(user: dict = Depends(require_health_consent)):
    return list_use_history(user["user_id"])


# 2. 복용 시작 기록 추가
@router.post("", status_code=201)
def create_history(
    data: HistoryCreateRequest,
    user: dict = Depends(require_health_consent),
):
    try:
        return add_use_history(
            user["user_id"],
            data.med_id,
            data.start_date,
            data.times_per_day,
            data.duration_days,
        )
    except MedNotRegisteredError:
        raise HTTPException(
            status_code=404,
            detail="내 약에 등록된 약을 찾을 수 없어요.",
        )
    except ActiveHistoryExistsError:
        raise HTTPException(
            status_code=409,
            detail="이미 복용 중이라고 기록된 약이에요.",
        )


# 3. 복용 시작일과 횟수 수정
@router.put("/{history_id}")
def change_history(
    history_id: int,
    data: HistoryUpdateRequest,
    user: dict = Depends(require_health_consent),
):
    try:
        return update_use_history(
            user["user_id"],
            history_id,
            data.start_date,
            data.times_per_day,
            data.duration_days,
        )
    except HistoryNotFoundError:
        raise HTTPException(
            status_code=404,
            detail="복용이력을 찾을 수 없어요.",
        )
    except InvalidHistoryDateError:
        raise HTTPException(
            status_code=400,
            detail="복용 시작일은 중단일보다 늦을 수 없어요.",
        )


# 4. 복용 중단 기록
@router.patch("/{history_id}/stop")
def stop_history(
    history_id: int,
    data: HistoryStopRequest,
    user: dict = Depends(require_health_consent),
):
    try:
        return stop_use_history(
            user["user_id"],
            history_id,
            data.stopped_at,
        )
    except InvalidHistoryDateError:
        raise HTTPException(
            status_code=400,
            detail="중단할 수 없는 기록이에요. 날짜나 기존 중단 상태를 확인해 주세요.",
        )
        
# 5. 복용이력 삭제
@router.delete("/{history_id}", status_code=204)
def remove_history(
    history_id: int,
    user: dict = Depends(require_health_consent),
):
    try:
        delete_use_history(user["user_id"], history_id)
    except HistoryNotFoundError:
        raise HTTPException(
            status_code=404,
            detail="복용이력을 찾을 수 없어요.",
        )