import smtplib
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from ..deps import get_current_user
from pydantic import BaseModel, Field, StringConstraints
from ..services.auth import create_user, login_user, create_token, get_user, email_taken, login_id_taken, find_login_id, reset_password, delete_user, agree_health, withdraw_health ,TOKEN_HOURS
from ..services.email_code import create_code, check_code, use_code, CODE_MINUTES
from ..services.mail import send_mail

COOKIE_NAME = "access_token"

Email = Annotated[str, StringConstraints(strip_whitespace=True, to_lower=True, max_length=255,
                                         pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")]
Code = Annotated[str, StringConstraints(strip_whitespace=True, pattern=r"^\d{6}$")]

router = APIRouter(
    prefix="/api/auth",
    tags=["Auth"]
)

class SignupRequest(BaseModel):
    login_id: str = Field(min_length=4, max_length=50)
    display_name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=30)]
    password: str = Field(min_length=8)
    email: Email
    email_code: Code
    agree_privacy: bool
    agree_health: bool = False

@router.get("/check-id")
def check_id(login_id: str = Query(min_length=4, max_length=50)):
    return {"available": not login_id_taken(login_id)}

@router.post("/signup", status_code=201)
def signup(data: SignupRequest):
    if not data.agree_privacy:
        raise HTTPException(status_code=400, detail="개인정보 수집에 동의해야 가입할 수 있어요.")

    code_id = check_code(data.email, "signup", data.email_code)
    if code_id is None:
        raise HTTPException(status_code=400, detail="인증번호가 맞지 않거나 시간이 지났어요.")

    user_id = create_user(data.login_id, data.password, data.display_name, data.agree_health, data.email)
    if user_id is None:
        raise HTTPException(status_code=409, detail="이미 사용 중인 아이디나 이메일이에요.")

    use_code(code_id)

    return {"user_id": user_id, "login_id": data.login_id, "display_name": data.display_name}

class LoginRequest(BaseModel):
    login_id: str
    password: str


@router.post("/login")
def login(data: LoginRequest, response: Response):
    user_id = login_user(data.login_id, data.password)
    if user_id is None:
        raise HTTPException(status_code=401, detail="아이디 또는 비밀번호가 맞지 않아요.")

    response.set_cookie(
        COOKIE_NAME,
        create_token(user_id),
        httponly=True,
        samesite="lax",
        max_age=TOKEN_HOURS * 3600,
    )
    return get_user(user_id)


@router.post("/logout")
def logout(response: Response):
    response.delete_cookie(COOKIE_NAME)
    return {"ok": True}


@router.get("/me")
def me(user: dict = Depends(get_current_user)):
    return user

class DeleteAccountRequest(BaseModel):
    password: str

@router.delete("/me")
def delete_me(data: DeleteAccountRequest, response: Response, user: dict = Depends(get_current_user)):
    # 관리자는 바로 탈퇴할 수 없어요: 관리자가 0명이 되면 화면으로는 아무도 관리자 화면에 못 들어가요
    # 관리자 권한을 먼저 해제(DB에서 role을 user로)한 뒤 탈퇴해요
    if user["role"] == "admin":
        raise HTTPException(status_code=409, detail="관리자 계정은 바로 탈퇴할 수 없어요. 관리자 권한을 먼저 해제해 주세요.")
    if not delete_user(user["user_id"], data.password):
        raise HTTPException(status_code=400, detail="비밀번호가 맞지 않아요.")
    response.delete_cookie(COOKIE_NAME)
    return {"ok": True}

@router.post("/consent/health")
def consent_health(user: dict = Depends(get_current_user)):
    agree_health(user["user_id"])
    return get_user(user["user_id"])

@router.delete("/consent/health")
def withdraw_consent_health(user: dict = Depends(get_current_user)):
    withdraw_health(user["user_id"])
    return get_user(user["user_id"])

class EmailCodeRequest(BaseModel):
    email: Email
    purpose: Literal["signup", "find_id", "reset_pw"]

@router.post("/email-code")
def email_code(data: EmailCodeRequest):
    taken = email_taken(data.email)
    if data.purpose == "signup" and taken:
        raise HTTPException(status_code=409, detail="이미 가입된 이메일이에요.")

    code = create_code(data.email, data.purpose)
    if code is None:
        raise HTTPException(status_code=429, detail="1분 뒤에 다시 요청해 주세요.")
    
    # 아이디 찾기·비밀번호 재설정은 가입 여부를 알려 주지 않는다 (번호만 만들고 메일은 보내지 않음)
    if data.purpose != "signup" and not taken:
        return {"ok": True}


    try:
        send_mail(
            data.email,
            "[약바로] 인증번호",
            f"인증번호는 {code} 입니다. {CODE_MINUTES}분 안에 입력해 주세요.",
        )
    except (smtplib.SMTPException, OSError):
        raise HTTPException(status_code=503, detail="메일을 보내지 못했어요. 잠시 후 다시 시도해 주세요.")
    return {"ok": True}

class FindIdRequest(BaseModel):
    email: Email
    email_code: Code

@router.post("/find-id")
def find_id(data: FindIdRequest):
    code_id = check_code(data.email, "find_id", data.email_code)
    login_id = find_login_id(data.email) if code_id else None
    if login_id is None:
        raise HTTPException(status_code=400, detail="인증번호가 맞지 않거나 시간이 지났어요.")

    use_code(code_id)
    return {"login_id": login_id}

class ResetPasswordRequest(BaseModel):
    email: Email
    email_code: Code
    password: str = Field(min_length=8, max_length=72)

@router.post("/reset-password")
def reset_pw(data: ResetPasswordRequest):
    code_id = check_code(data.email, "reset_pw", data.email_code)
    if code_id is None or not reset_password(data.email, data.password):
        raise HTTPException(status_code=400, detail="인증번호가 맞지 않거나 시간이 지났어요.")

    use_code(code_id)
    return {"ok": True}