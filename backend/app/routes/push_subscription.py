import os

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from ..deps import get_current_user, require_health_consent
from ..services.push_subscription import (
    SubscriptionInUseError,
    delete_subscription,
    save_subscription,
)


router = APIRouter(
    prefix="/api/push",
    tags=["PushSubscription"],
)


# 브라우저의 푸시 암호화 정보
class SubscriptionKeys(BaseModel):
    p256dh: str = Field(min_length=1)
    auth: str = Field(min_length=1)


# 구독 등록 요청
class SubscriptionCreateRequest(BaseModel):
    endpoint: str = Field(min_length=1)
    keys: SubscriptionKeys


# 구독 해제 요청
class SubscriptionDeleteRequest(BaseModel):
    endpoint: str = Field(min_length=1)


# 1. VAPID 공개키 조회
@router.get("/public-key")
def get_public_key():
    public_key = os.getenv("VAPID_PUBLIC_KEY")

    if not public_key:
        raise HTTPException(
            status_code=503,
            detail="푸시 알림 설정이 준비되지 않았어요.",
        )

    return {"public_key": public_key}


# 2. 브라우저 푸시 구독 등록
@router.post("/subscribe", status_code=201)
def subscribe(
    data: SubscriptionCreateRequest,
    user: dict = Depends(require_health_consent),
):
    try:
        return save_subscription(
            user["user_id"],
            data.endpoint,
            data.keys.p256dh,
            data.keys.auth,
        )

    except SubscriptionInUseError:
        raise HTTPException(
            status_code=409,
            detail="다른 계정에 등록된 구독 정보예요.",
        )


# 3. 브라우저 푸시 구독 해제
@router.delete("/subscribe")
def unsubscribe(
    data: SubscriptionDeleteRequest,
    user: dict = Depends(get_current_user),
):
    deleted = delete_subscription(
        user["user_id"],
        data.endpoint,
    )

    if not deleted:
        raise HTTPException(
            status_code=404,
            detail="구독 정보를 찾을 수 없어요.",
        )

    return {"message": "푸시 알림 구독을 해제했어요."}