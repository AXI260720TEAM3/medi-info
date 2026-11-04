from datetime import datetime, timedelta, timezone

import jwt
from pwdlib import PasswordHash
from pwdlib.hashers.bcrypt import BcryptHasher
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from ..config import JWT_SECRET
from ..database import SessionLocal

# 믹서기: bcrypt 방식으로 갈아요
password_hash = PasswordHash((BcryptHasher(),))

# 약관을 고치면 이 값을 올려요 → 동의 기록에 어느 약관에 동의했는지 남아요
TERMS_VERSION = "2026-11-2"

# 입장 팔찌 유효 시간
TOKEN_HOURS = 12

def hash_password(password:str) -> str:
    return password_hash.hash(password)

def verify_password(password: str, hashed: str) -> bool:
    return password_hash.verify(password, hashed)


def create_user(login_id: str, password: str, display_name: str, agree_health: bool, email: str):
    consents = ["개인정보"]
    if agree_health:
        consents.append("건강정보")

    with SessionLocal() as db:
        try:
            user_id = db.execute(
                text("""
                    INSERT INTO app_user (login_id, display_name, password_hash, email, email_verified_at)
                    VALUES (:login_id, :display_name, :password_hash, :email, now())
                    RETURNING user_id
                """),
                {"login_id": login_id, "display_name": display_name, "password_hash": hash_password(password), "email": email},
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

def login_user(login_id: str, password: str):
    with SessionLocal() as db:
        row = db.execute(
            text("SELECT user_id, password_hash FROM app_user WHERE login_id = :login_id"),
            {"login_id": login_id},
        ).first()
        if row is None or not verify_password(password, row.password_hash):
            return None

        db.execute(
            text("UPDATE app_user SET last_login_at = now() WHERE user_id = :user_id"),
            {"user_id": row.user_id},
        )
        db.commit()
    return row.user_id

def create_token(user_id: int) -> str:
    expire = datetime.now(timezone.utc) + timedelta(hours=TOKEN_HOURS)
    return jwt.encode({"sub": str(user_id), "exp": expire}, JWT_SECRET, algorithm="HS256")

def read_token(token: str):
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
    except jwt.InvalidTokenError:
        return None
    return int(payload["sub"])


def get_user(user_id: int):
    with SessionLocal() as db:
        row = db.execute(
            text("SELECT user_id, login_id, display_name, role FROM app_user WHERE user_id = :user_id"),
            {"user_id": user_id},
        ).mappings().first()
    return dict(row) if row else None

def email_taken(email: str) -> bool:
    with SessionLocal() as db:
        return db.execute(
            text("SELECT 1 FROM app_user WHERE email = :email"),
            {"email": email},
        ).first() is not None

def login_id_taken(login_id: str) -> bool:
    with SessionLocal() as db:
        return db.execute(
            text("SELECT 1 FROM app_user WHERE login_id = :login_id"),
            {"login_id": login_id},
        ).first() is not None

def find_login_id(email: str):
    with SessionLocal() as db:
        return db.execute(
            text("SELECT login_id FROM app_user WHERE email = :email"),
            {"email":email},
        ).scalar()

def reset_password(email: str, password: str) -> bool:
    with SessionLocal() as db:
        result = db.execute(
            text("UPDATE app_user SET password_hash = :password_hash WHERE email = :email"),
            {"password_hash": hash_password(password), "email": email},
        )
        db.commit()
    return result.rowcount == 1