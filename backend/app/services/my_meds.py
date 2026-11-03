from sqlalchemy import text
from ..database import SessionLocal


def list_meds(user_id: int) -> list[dict]:
    with SessionLocal() as db:
        rows = db.execute(
            text("SELECT med_id, item_seq, item_name FROM user_med WHERE user_id = :user_id"),
            {"user_id": user_id},
        ).mappings().all()
    return [dict(row) for row in rows]


def add_med(user_id: int, item_seq: str, item_name: str) -> dict | None:
    params = {"user_id": user_id, "item_seq": item_seq, "item_name": item_name}
    with SessionLocal() as db:
        exists = db.execute(
            text("SELECT 1 FROM user_med WHERE user_id = :user_id AND item_seq = :item_seq"),
            params,
        ).first()
        if exists:
            return None

        row = db.execute(
            text("""
                INSERT INTO user_med (user_id, item_seq, item_name)
                VALUES (:user_id, :item_seq, :item_name)
                RETURNING med_id, item_seq, item_name
            """),
            params,
        ).mappings().one()
        db.commit()
    return dict(row)


def delete_med(user_id: int, med_id: int) -> bool:
    with SessionLocal() as db:
        result = db.execute(
            text("DELETE FROM user_med WHERE med_id = :med_id AND user_id = :user_id"),
            {"med_id": med_id, "user_id": user_id},
        )
        db.commit()
    return result.rowcount > 0
