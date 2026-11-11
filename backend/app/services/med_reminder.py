
from datetime import time

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from ..database import SessionLocal


class HistoryUnavailableError(Exception):
    pass


class ReminderAlreadyExistsError(Exception):
    pass


def list_reminders(user_id: int):
    """로그인한 사용자의 복약 알림 목록"""

    with SessionLocal() as db:
        rows = db.execute(
            text("""
                SELECT
                    r.reminder_id,
                    r.history_id,
                    h.item_name,
                    r.remind_time,
                    r.timezone,
                    r.is_enabled,
                    h.start_date,
                    h.stopped_at
                FROM public.med_reminder r
                JOIN public.med_use_history h
                    ON r.history_id = h.history_id
                WHERE h.user_id = :user_id
                ORDER BY h.start_date DESC, r.remind_time ASC
            """),
            {"user_id": user_id},
        ).mappings().all()

        return [dict(row) for row in rows]


def add_reminder(
    user_id: int,
    history_id: int,
    remind_time: time,
):
    """복용 중인 약에 알림 시간 추가"""

    with SessionLocal() as db:
        try:
            row = db.execute(
                text("""
                    INSERT INTO public.med_reminder (
                        history_id,
                        remind_time
                    )
                    SELECT
                        h.history_id,
                        :remind_time
                    FROM public.med_use_history h
                    WHERE h.history_id = :history_id
                      AND h.user_id = :user_id
                      AND h.stopped_at IS NULL
                    RETURNING
                        reminder_id,
                        history_id,
                        remind_time,
                        timezone,
                        is_enabled
                """),
                {
                    "user_id": user_id,
                    "history_id": history_id,
                    "remind_time": remind_time,
                },
            ).mappings().first()

            if row is None:
                raise HistoryUnavailableError()

            result = dict(row)
            db.commit()
            return result

        except IntegrityError as exc:
            db.rollback()
            raise ReminderAlreadyExistsError() from exc

class ReminderNotFoundError(Exception):
    pass


def update_reminder(
    user_id: int,
    reminder_id: int,
    remind_time: time,
    is_enabled: bool,
):
    """내 알림 시간과 활성화 상태 수정"""

    with SessionLocal() as db:
        try:
            row = db.execute(
                text("""
                    UPDATE public.med_reminder r
                    SET
                        remind_time = :remind_time,
                        is_enabled = :is_enabled
                    FROM public.med_use_history h
                    WHERE r.history_id = h.history_id
                      AND r.reminder_id = :reminder_id
                      AND h.user_id = :user_id
                      AND h.stopped_at IS NULL
                    RETURNING
                        r.reminder_id,
                        r.history_id,
                        r.remind_time,
                        r.timezone,
                        r.is_enabled
                """),
                {
                    "user_id": user_id,
                    "reminder_id": reminder_id,
                    "remind_time": remind_time,
                    "is_enabled": is_enabled,
                },
            ).mappings().first()

            if row is None:
                raise ReminderNotFoundError()

            result = dict(row)
            db.commit()
            return result

        except IntegrityError as exc:
            db.rollback()
            raise ReminderAlreadyExistsError() from exc


def delete_reminder(user_id: int, reminder_id: int):
    """내 알림 삭제"""

    with SessionLocal() as db:
        row = db.execute(
            text("""
                DELETE FROM public.med_reminder r
                USING public.med_use_history h
                WHERE r.history_id = h.history_id
                  AND r.reminder_id = :reminder_id
                  AND h.user_id = :user_id
                RETURNING r.reminder_id
            """),
            {
                "user_id": user_id,
                "reminder_id": reminder_id,
            },
        ).first()

        if row is None:
            raise ReminderNotFoundError()

        db.commit()
        return {"message": "복약 알림을 삭제했어요."}