import logging
import time

from sqlalchemy import text

from ..database import SessionLocal
from .push_sender import send_test_push


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def send_due_reminders():
    """설정 시간이 된 알림과 실패한 발송 작업 처리"""

    with SessionLocal() as db:
        reminders = db.execute(
            text("""
                SELECT
                    r.reminder_id,
                    p.subscription_id,
                    d.scheduled_date
                FROM public.med_reminder r
                JOIN public.med_use_history h
                    ON r.history_id = h.history_id
                JOIN public.push_subscription p
                    ON p.user_id = h.user_id
                CROSS JOIN LATERAL (
                    SELECT
                        (now() AT TIME ZONE r.timezone)::date
                        + day_offset AS scheduled_date
                    FROM (VALUES (0), (-1)) AS days(day_offset)
                ) d
                CROSS JOIN LATERAL (
                    SELECT (
                        (d.scheduled_date + r.remind_time)
                        AT TIME ZONE r.timezone
                    ) AS due_at
                ) t
                WHERE r.is_enabled = TRUE
                  AND h.stopped_at IS NULL
                  AND h.start_date <= d.scheduled_date
                  AND (
                      h.duration_days IS NULL
                      OR d.scheduled_date < h.start_date + h.duration_days
                )
                 AND(
                      t.due_at BETWEEN
                          now() - INTERVAL '5 minutes'
                          AND now()
                      OR (
                          t.due_at BETWEEN
                              now() - INTERVAL '30 minutes'
                              AND now()
                          AND EXISTS (
                              SELECT 1
                              FROM public.push_delivery_log l
                              WHERE l.reminder_id = r.reminder_id
                                AND l.subscription_id = p.subscription_id
                                AND l.scheduled_date = d.scheduled_date
                                AND l.status IN ('failed', 'sending')
                                AND l.attempt_count < 3
                          )
                      )
                  )
            """)
        ).mappings().all()

    for reminder in reminders:
        subscription_id = reminder["subscription_id"]

        # 다른 작업이 이미 처리 중이면 선점하지 않음
        with SessionLocal() as db:
            delivery_id = db.execute(
                text("""
                    INSERT INTO public.push_delivery_log (
                        reminder_id,
                        subscription_id,
                        scheduled_date,
                        status,
                        attempt_count,
                        last_attempt_at
                    )
                    VALUES (
                        :reminder_id,
                        :subscription_id,
                        :scheduled_date,
                        'sending',
                        1,
                        now()
                    )
                    ON CONFLICT (
                        reminder_id,
                        subscription_id,
                        scheduled_date
                    )
                    DO UPDATE SET
                        status = 'sending',
                        attempt_count =
                            push_delivery_log.attempt_count + 1,
                        last_attempt_at = now()
                    WHERE push_delivery_log.attempt_count < 3
                      AND (
                          (
                              push_delivery_log.status = 'failed'
                              AND push_delivery_log.last_attempt_at
                                  <= now() - INTERVAL '30 seconds'
                          )
                          OR (
                              push_delivery_log.status = 'sending'
                              AND push_delivery_log.last_attempt_at
                                  <= now() - INTERVAL '2 minutes'
                          )
                      )
                    RETURNING delivery_id
                """),
                {
                    "reminder_id": reminder["reminder_id"],
                    "subscription_id": subscription_id,
                    "scheduled_date": reminder["scheduled_date"],
                },
            ).scalar_one_or_none()

            db.commit()

        if delivery_id is None:
            continue

        try:
            send_test_push(subscription_id)

        except Exception:
            logger.exception(
                "푸시 발송 실패: delivery_id=%s",
                delivery_id,
            )

            with SessionLocal() as db:
                db.execute(
                    text("""
                        UPDATE public.push_delivery_log
                        SET status = 'failed'
                        WHERE delivery_id = :delivery_id
                    """),
                    {"delivery_id": delivery_id},
                )
                db.commit()

        else:
            with SessionLocal() as db:
                db.execute(
                    text("""
                        UPDATE public.push_delivery_log
                        SET
                            status = 'sent',
                            sent_at = now()
                        WHERE delivery_id = :delivery_id
                    """),
                    {"delivery_id": delivery_id},
                )
                db.commit()

            logger.info(
                "푸시 발송 완료: delivery_id=%s",
                delivery_id,
            )


def mark_abandoned_deliveries():
    """재시도할 수 없는 오래된 발송 작업 정리"""

    with SessionLocal() as db:
        db.execute(
            text("""
                UPDATE public.push_delivery_log
                SET status = 'failed'
                WHERE status = 'sending'
                  AND (
                      (
                          attempt_count >= 3
                          AND last_attempt_at
                              <= now() - INTERVAL '2 minutes'
                      )
                      OR last_attempt_at
                          <= now() - INTERVAL '30 minutes'
                  )
            """)
        )
        db.commit()


if __name__ == "__main__":
    logger.info("복약 알림 자동 발송 작업 시작")

    while True:
        try:
            send_due_reminders()
            mark_abandoned_deliveries()
        except Exception:
            logger.exception("복약 알림 자동 작업 오류")

        time.sleep(15)