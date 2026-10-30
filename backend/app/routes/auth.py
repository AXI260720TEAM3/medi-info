from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from ..services.auth import create_user

router = APIRouter(
    prefix="/api/auth",
    tags=["Auth"]
)

class SignupRequest(BaseModel):
    login_id: str = Field(min_length=4, max_length=50)
    password: str = Field(min_length=8)
    agree_privacy: bool
    agree_health: bool = False

@router.post("/signup", status_code=201)
def signup(data: SignupRequest):
    if not data.agree_privacy:
        raise HTTPException(status_code=400, detail="개인정보 수집에 동의해야 가입할 수 있어요.")

    user_id = create_user(data.login_id, data.password, data.agree_health)
    if user_id is None:
        raise HTTPException(status_code=409, detail="이미 사용 중인 아이디예요.")

    return {"user_id": user_id, "login_id": data.login_id}