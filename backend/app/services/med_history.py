
from datetime import date

from sqlalchemy import text
from ..database import SessionLocal


class MedNotRegisteredError(Exception):
    pass


class ActiveHistoryExistsError(Exception):
    pass


class HistoryNotFoundError(Exception):
    pass


class InvalidHistoryDateError(Exception):
    pass


# 1. 복용이력 전체 조회
def list_use_history(user_id: int) -> list[dict]:
    with SessionLocal() as db:
        rows = db.execute(
            text("""
                SELECT history_id, item_seq, item_name,
                       start_date, times_per_day,
                       duration_days, stopped_at
                FROM med_use_history
                WHERE user_id = :user_id
                ORDER BY start_date DESC, history_id DESC
            """),
            {"user_id": user_id},
        ).mappings().all()

    return [dict(row) for row in rows]


# 2. 복용 시작 기록 추가
def add_use_history(
    user_id: int,
    med_id: int,
    start_date: date,
    times_per_day: int | None,
    duration_days: int | None = None,
) -> dict:
    with SessionLocal() as db:
        # 내 약에 등록된 약인지 확인
        med = db.execute(
            text("""
                SELECT item_seq, item_name
                FROM user_med
                WHERE med_id = :med_id AND user_id = :user_id
                FOR UPDATE
            """),
            {"med_id": med_id, "user_id": user_id},
        ).mappings().one_or_none()

        if med is None:
            raise MedNotRegisteredError()

        # 복용 기간이 겹치는 진행 중 기록 확인
        exists = db.execute(
            text("""
                SELECT 1
                FROM med_use_history
                WHERE user_id = :user_id
                  AND item_seq = :item_seq
                  AND stopped_at IS NULL
                  AND (
                      duration_days IS NULL
                      OR start_date + (duration_days - 1)
                          >= :start_date
                  )
            """),
            {
                "user_id": user_id,
                "item_seq": med["item_seq"],
                "start_date": start_date,
            },
        ).first()

        if exists:
            raise ActiveHistoryExistsError()

        row = db.execute(
            text("""
                INSERT INTO med_use_history (
                    user_id, item_seq, item_name,
                    start_date, times_per_day, duration_days
                )
                VALUES (
                    :user_id, :item_seq, :item_name,
                    :start_date, :times_per_day, :duration_days
                )
                RETURNING history_id, item_seq, item_name,
                          start_date, times_per_day,
                          duration_days, stopped_at
            """),
            {
                "user_id": user_id,
                "item_seq": med["item_seq"],
                "item_name": med["item_name"],
                "start_date": start_date,
                "times_per_day": times_per_day,
                "duration_days": duration_days,
            },
        ).mappings().one()

        db.commit()

    return dict(row)


# 3. 복용 시작일, 횟수, 기간 수정
def update_use_history(
    user_id: int,
    history_id: int,
    start_date: date,
    times_per_day: int | None,
    duration_days: int | None = None,
) -> dict:
    with SessionLocal() as db:
        history = db.execute(
            text("""
                SELECT stopped_at
                FROM med_use_history
                WHERE history_id = :history_id
                  AND user_id = :user_id
                FOR UPDATE
            """),
            {"history_id": history_id, "user_id": user_id},
        ).mappings().one_or_none()

        if history is None:
            raise HistoryNotFoundError()

        if history["stopped_at"] is not None:
            if start_date > history["stopped_at"]:
                raise InvalidHistoryDateError()

        row = db.execute(
            text("""
                UPDATE med_use_history
                SET start_date = :start_date,
                    times_per_day = :times_per_day,
                    duration_days = :duration_days
                WHERE history_id = :history_id
                  AND user_id = :user_id
                RETURNING history_id, item_seq, item_name,
                          start_date, times_per_day,
                          duration_days, stopped_at
            """),
            {
                "history_id": history_id,
                "user_id": user_id,
                "start_date": start_date,
                "times_per_day": times_per_day,
                "duration_days": duration_days,
            },
        ).mappings().one()

        db.commit()

    return dict(row)


# 4. 복용 중단 기록
def stop_use_history(
    user_id: int,
    history_id: int,
    stopped_at: date,
) -> dict:
    with SessionLocal() as db:
        row = db.execute(
            text("""
                UPDATE med_use_history
                SET stopped_at = :stopped_at
                WHERE history_id = :history_id
                  AND user_id = :user_id
                  AND stopped_at IS NULL
                  AND start_date <= :stopped_at
                RETURNING history_id, item_seq, item_name,
                          start_date, times_per_day,
                          duration_days, stopped_at
            """),
            {
                "history_id": history_id,
                "user_id": user_id,
                "stopped_at": stopped_at,
            },
        ).mappings().one_or_none()

        if row is None:
            raise InvalidHistoryDateError()

        db.commit()

    return dict(row)

# 5. 복용이력 삭제
def delete_use_history(user_id: int, history_id: int) -> None:
    with SessionLocal() as db:
        deleted_id = db.execute(
            text("""
                DELETE FROM med_use_history
                WHERE history_id = :history_id
                  AND user_id = :user_id
                RETURNING history_id
            """),
            {
                "history_id": history_id,
                "user_id": user_id,
            },
        ).scalar_one_or_none()

        if deleted_id is None:
            raise HistoryNotFoundError()

        db.commit()