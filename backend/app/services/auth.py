from pwdlib import PasswordHash
from pwdlib.hashers.bcrypt import BcryptHasher
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from ..database import SessionLocal

# 믹서기: bcrypt 방식으로 갈아요
password_hash = PasswordHash((BcryptHasher(),))

# 약관을 고치면 이 값을 올려요 → 동의 기록에 어느 약관에 동의했는지 남아요
TERMS_VERSION = "2026-10"


def hash_password(password:str) -> str:
    return password_hash.hash(password)

def verify_password(password: str, hashed: str) -> bool:
    return password_hash.verify(password, hashed)


def create_user(login_id: str, password: str, agree_health: bool):
    consents = ["개인정보"]
    if agree_health:
        consents.append("건강정보")

    with SessionLocal() as db:
        try:
            user_id = db.execute(
                text("""
                    INSERT INTO app_user (login_id, password_hash)
                    VALUES (:login_id, :password_hash)
                    RETURNING user_id
                """),
                {"login_id": login_id, "password_hash": hash_password(password)},
            ).scalar_one()

            for consent_type in consents:
                db.execute(
                    text("""
                        INSERT INTO user_consent (user_id, consent_type, terms_version)
                        VALUES (:user_id, :consent_type, :terms_version)
                    """),
                    {"user_id": user_id, "consent_type": consent_type, "terms_version": TERMS_VERSION},
                )
            db.commit()
        except IntegrityError:
            db.rollback()
            return None
    return user_id