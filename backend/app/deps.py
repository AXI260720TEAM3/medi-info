from fastapi import Cookie, HTTPException
from .services.auth import read_token, get_user

def get_current_user(access_token: str | None = Cookie(default=None)):     
    user_id = read_token(access_token) if access_token else None
    user = get_user(user_id) if user_id else None
    if user is None:
        raise HTTPException(status_code=401, detail="로그인이 필요해요.")
    return user