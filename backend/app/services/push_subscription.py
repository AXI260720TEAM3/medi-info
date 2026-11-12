from sqlalchemy import text

from ..database import SessionLocal


class SubscriptionInUseError(Exception):
    pass


def save_subscription(
    user_id: int,
    endpoint: str,
    p256dh: str,
    auth: str,
):
    """로그인한 사용자의 푸시 구독 저장"""

    with SessionLocal() as db:
        subscription_id = db.execute(
            text("""
                INSERT INTO public.push_subscription (
                    user_id, endpoint, p256dh, auth
                )
                VALUES (
                    :user_id, :endpoint, :p256dh, :auth
                )
                ON CONFLICT (endpoint)
                DO UPDATE SET
                    p256dh = EXCLUDED.p256dh,
                    auth = EXCLUDED.auth,
                    updated_at = now()
                WHERE public.push_subscription.user_id = EXCLUDED.user_id
                RETURNING subscription_id
            """),
            {
                "user_id": user_id,
                "endpoint": endpoint,
                "p256dh": p256dh,
                "auth": auth,
            },
        ).scalar_one_or_none()

        if subscription_id is None:
            db.rollback()
            raise SubscriptionInUseError()

        db.commit()
        return {"subscription_id": subscription_id}


def delete_subscription(user_id: int, endpoint: str):
    """로그인한 사용자의 푸시 구독 해제"""

    with SessionLocal() as db:
        result = db.execute(
            text("""
                DELETE FROM public.push_subscription
                WHERE user_id = :user_id
                  AND endpoint = :endpoint
                RETURNING subscription_id
            """),
            {
                "user_id": user_id,
                "endpoint": endpoint,
            },
        ).scalar_one_or_none()

        db.commit()
        return result is not None