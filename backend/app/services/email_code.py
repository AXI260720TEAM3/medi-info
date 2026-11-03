import hashlib
import hmac
import secrets

from sqlalchemy import text

from ..config import JWT_SECRET
from ..database import SessionLocal

CODE_MINUTES = 10 # 인증번호 유효시간
MAX_ATTEMPTS = 5 # 틀릴 수 있는 횟수
RESEND_SECONDS = 60 # 다시 받으려면 기다리는 시간


def _hash(code: str) -> str:
    return hmac.new(JWT_SECRET.encode(), code.encode(), hashlib.sha256).hexdigest()

def create_code(email: str, purpose:str):
    """새 인증번호를 만들어 저장하고 돌려준다. 1분 안에 다시 요청하면 None."""
    with SessionLocal() as db:
        recent = db.execute(
            text("""
                SELECT 1 FROM email_code
                WHERE email = :email AND purpose = :purpose
                  AND created_at > now() - make_interval(secs => :secs)
            """),
            {"email": email, "purpose": purpose, "secs": RESEND_SECONDS},
        ).first()
        if recent:
            return None

        code = f"{secrets.randbelow(1_000_000):06d}"
        db.execute(
            text("""
                INSERT INTO email_code (email, purpose, code_hash, expires_at)
                VALUES (:email, :purpose, :code_hash, now() + make_interval(mins => :mins))
            """),
            {"email": email, "purpose": purpose, "code_hash": _hash(code), "mins": CODE_MINUTES},
        )
        db.commit()
    return code

def check_code(email: str, purpose: str, code: str):
    """맞으면 code_id, 틀리거나 만료됐으면 None. 사용 처리는 use_code가 한다."""
    with SessionLocal() as db:
        row = db.execute(
            text("""
                SELECT code_id, code_hash, attempts FROM email_code
                WHERE email = :email AND purpose = :purpose
                  AND used_at IS NULL AND expires_at > now()
                ORDER BY created_at DESC
                LIMIT 1
            """),
            {"email":email, "purpose": purpose},
        ).first()
        if row is None or row.attempts >= MAX_ATTEMPTS:
            return None

        if not hmac.compare_digest(row.code_hash, _hash(code)):
            db.execute(
                text("UPDATE email_code SET attempts = attempts + 1 WHERE code_id = :code_id"),
                {"code_id": row.code_id},
            )
            db.commit()
            return None
    return row.code_id


def use_code(code_id: int):
    with SessionLocal() as db:
        db.execute(
            text("UPDATE email_code SET used_at = now() WHERE code_id = :code_id"),
            {"code_id": code_id},
        )
        db.commit()
        