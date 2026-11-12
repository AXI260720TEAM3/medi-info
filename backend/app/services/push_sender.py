import os
from urllib.parse import urlparse

from pywebpush import webpush
from sqlalchemy import text

from ..database import SessionLocal


def send_test_push(subscription_id: int):
    """등록된 브라우저로 테스트 푸시 발송"""

    private_key = os.getenv("VAPID_PRIVATE_KEY")
    vapid_subject = os.getenv(
       "VAPID_SUBJECT",
        "https://github.com",
)

    if not private_key:
        raise RuntimeError("VAPID 비밀키가 없어요.")

    # DB에서 구독 정보 가져오기
    with SessionLocal() as db:
        subscription = db.execute(
            text("""
                SELECT endpoint, p256dh, auth
                FROM public.push_subscription
                WHERE subscription_id = :subscription_id
            """),
            {"subscription_id": subscription_id},
        ).mappings().first()

    if subscription is None:
        raise ValueError("푸시 구독을 찾을 수 없어요.")

    # 이번 테스트는 확인된 Chrome 푸시 서버로만 발송
    endpoint = subscription["endpoint"]

    if (
        urlparse(endpoint).scheme != "https"
        or urlparse(endpoint).hostname != "fcm.googleapis.com"
    ):
        raise ValueError("테스트 대상 푸시 서버가 아니에요.")

    response = webpush(
        subscription_info={
            "endpoint": endpoint,
            "keys": {
                "p256dh": subscription["p256dh"],
                "auth": subscription["auth"],
            },
        },
        data="약바로 서버 푸시 테스트",
        vapid_private_key=private_key,
        vapid_claims={
            "sub": vapid_subject,
        },
        ttl=60,
        timeout=15,
    )

    return {
        "success": True,
        "status_code": response.status_code,
    }