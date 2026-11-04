from fastapi import Cookie, Depends, HTTPException
from .services.auth import read_token, get_user

def get_current_user(access_token: str | None = Cookie(default=None)):     
    user_id = read_token(access_token) if access_token else None
    user = get_user(user_id) if user_id else None
    if user is None:
        raise HTTPException(status_code=401, detail="로그인이 필요해요.")
    return user

def require_health_consent(user: dict = Depends(get_current_user)):
    if not user["agree_health"]:
        raise HTTPException(status_code=403, detail="건강정보 수집에 동의해야 쓸 수 있어요.")
    return user

