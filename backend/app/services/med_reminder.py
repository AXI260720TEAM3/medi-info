
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
                    r.alarm_label,
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
    alarm_label: str | None = None,
):
    """복용 중인 약에 알림 시간 추가"""

    with SessionLocal() as db:
        try:
            row = db.execute(
                text("""
                    INSERT INTO public.med_reminder (
                        history_id,
                        remind_time,
                        alarm_label
                    )
                    SELECT
                        h.history_id,
                        :remind_time,
                        :alarm_label
                    FROM public.med_use_history h
                    WHERE h.history_id = :history_id
                      AND h.user_id = :user_id
                      AND h.stopped_at IS NULL
                    RETURNING
                        reminder_id,
                        history_id,
                        remind_time,
                        alarm_label,
                        timezone,
                        is_enabled
                """),
                {
                    "user_id": user_id,
                    "history_id": history_id,
                    "remind_time": remind_time,
                    "alarm_label": alarm_label,
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


def add_reminders_bulk(
    user_id: int,
    history_id: int,
    remind_times: list[time],
):
    """복약 알람 시간을 한 번에 설정하거나 변경"""

    if not 1 <= len(remind_times) <= 24:
        raise ValueError("알람 시간은 1~24개 등록할 수 있어요.")

    if len(set(remind_times)) != len(remind_times):
        raise ValueError("중복된 알람 시간이 있어요.")

    with SessionLocal() as db:
        history = db.execute(
            text("""
                SELECT times_per_day
                FROM public.med_use_history
                WHERE history_id = :history_id
                  AND user_id = :user_id
                  AND stopped_at IS NULL
                FOR UPDATE
            """),
            {
                "history_id": history_id,
                "user_id": user_id,
            },
        ).mappings().one_or_none()

        if history is None:
            raise HistoryUnavailableError()

        times_per_day = history["times_per_day"]

        if (
            times_per_day is not None
            and len(remind_times) != times_per_day
        ):
            raise ValueError(
                "하루 복용 횟수와 알람 시간 개수가 달라요."
            )

        try:
            existing = db.execute(
                text("""
                    SELECT reminder_id, remind_time
                    FROM public.med_reminder
                    WHERE history_id = :history_id
                    FOR UPDATE
                """),
                {"history_id": history_id},
            ).mappings().all()

            requested_times = set(remind_times)
            existing_times = {
                row["remind_time"] for row in existing
            }

            # 새 설정에 없는 기존 알람만 삭제
            for row in existing:
                if row["remind_time"] not in requested_times:
                    db.execute(
                        text("""
                            DELETE FROM public.med_reminder
                            WHERE reminder_id = :reminder_id
                        """),
                        {"reminder_id": row["reminder_id"]},
                    )

            # 아직 없는 알람 시간만 추가
            for remind_time in remind_times:
                if remind_time not in existing_times:
                    db.execute(
                        text("""
                            INSERT INTO public.med_reminder (
                                history_id,
                                remind_time
                            )
                            VALUES (
                                :history_id,
                                :remind_time
                            )
                        """),
                        {
                            "history_id": history_id,
                            "remind_time": remind_time,
                        },
                    )

            results = db.execute(
                text("""
                    SELECT
                        reminder_id,
                        history_id,
                        remind_time,
                        timezone,
                        is_enabled
                    FROM public.med_reminder
                    WHERE history_id = :history_id
                    ORDER BY remind_time
                """),
                {"history_id": history_id},
            ).mappings().all()

            db.commit()
            return [dict(row) for row in results]

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
    alarm_label: str | None = None,
):
    """내 알림 시간과 활성화 상태 수정"""

    with SessionLocal() as db:
        try:
            row = db.execute(
                text("""
                    UPDATE public.med_reminder r
                    SET
                        remind_time = :remind_time,
                        is_enabled = :is_enabled,
                        alarm_label = COALESCE(:alarm_label, r.alarm_label)
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
                        r.is_enabled,
                        r.alarm_label
                """),
                {
                    "user_id": user_id,
                    "reminder_id": reminder_id,
                    "remind_time": remind_time,
                    "is_enabled": is_enabled,
                    "alarm_label": alarm_label,
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