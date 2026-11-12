
from datetime import time
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from ..deps import require_health_consent
from ..services.med_reminder import (
    HistoryUnavailableError,
    ReminderAlreadyExistsError,
    add_reminder,
    list_reminders,
    ReminderNotFoundError,
    update_reminder,
    delete_reminder,
    add_reminders_bulk,
)


router = APIRouter(
    prefix="/api/med-reminders",
    tags=["MedReminder"],
)


# 알림 등록 시 받는 정보
class ReminderCreateRequest(BaseModel):
    history_id: int = Field(gt=0)
    remind_time: time
    alarm_label: Literal[
        "아침", "점심", "저녁", "취침 전", "식전", "식후"
    ] | None = None

# 알람 시간 일괄 등록 시 받는 정보
class ReminderBulkCreateRequest(BaseModel):
    history_id: int = Field(gt=0)
    remind_times: list[time] = Field(min_length=1, max_length=24)

# 알림 수정 시 받는 정보
class ReminderUpdateRequest(BaseModel):
    remind_time: time
    is_enabled: bool
    alarm_label: Literal[
        "아침", "점심", "저녁", "취침 전", "식전", "식후"
    ] | None = None

# 1. 내 복약 알림 목록 조회
@router.get("")
def get_reminders(
    user: dict = Depends(require_health_consent),
):
    return list_reminders(user["user_id"])


# 2. 복약 알림 시간 등록
@router.post("", status_code=201)
def create_reminder(
    data: ReminderCreateRequest,
    user: dict = Depends(require_health_consent),
):
    try:
        return add_reminder(
            user["user_id"],
            data.history_id,
            data.remind_time,
            data.alarm_label,
        )

    except HistoryUnavailableError:
        raise HTTPException(
            status_code=404,
            detail="복용 중인 약의 기록을 찾을 수 없어요.",
        )

    except ReminderAlreadyExistsError:
        raise HTTPException(
            status_code=409,
            detail="이미 등록된 알림 시간이에요.",
        )


# 복약 알람 시간 일괄 등록
@router.post("/bulk", status_code=201)
def create_reminders_bulk(
    data: ReminderBulkCreateRequest,
    user: dict = Depends(require_health_consent),
):
    try:
        return add_reminders_bulk(
            user["user_id"],
            data.history_id,
            data.remind_times,
        )

    except HistoryUnavailableError:
        raise HTTPException(
            status_code=404,
            detail="복용 중인 약의 기록을 찾을 수 없어요.",
        )

    except ReminderAlreadyExistsError:
        raise HTTPException(
            status_code=409,
            detail="이미 등록된 알람 시간이 있어요.",
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )


# 3. 복약 알림 시간 및 활성화 상태 수정
@router.put("/{reminder_id}")
def change_reminder(
    reminder_id: int,
    data: ReminderUpdateRequest,
    user: dict = Depends(require_health_consent),
):
    try:
        return update_reminder(
            user["user_id"],
            reminder_id,
            data.remind_time,
            data.is_enabled,
            data.alarm_label,
        )

    except ReminderNotFoundError:
        raise HTTPException(
            status_code=404,
            detail="수정할 수 있는 복약 알림을 찾지 못했어요.",
        )

    except ReminderAlreadyExistsError:
        raise HTTPException(
            status_code=409,
            detail="이미 등록된 알림 시간이에요.",
        )


# 4. 복약 알림 삭제
@router.delete("/{reminder_id}")
def remove_reminder(
    reminder_id: int,
    user: dict = Depends(require_health_consent),
):
    try:
        return delete_reminder(
            user["user_id"],
            reminder_id,
        )

    except ReminderNotFoundError:
        raise HTTPException(
            status_code=404,
            detail="삭제할 복약 알림을 찾지 못했어요.",
        )
