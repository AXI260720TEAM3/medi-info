from fastapi import Cookie, Depends, HTTPException, Request
from .config import ADMIN_HOSTS
from .services.auth import read_token, get_user

def get_current_user(access_token: str | None = Cookie(default=None)):     
    user_id = read_token(access_token) if access_token else None
    user = get_user(user_id) if user_id else None
    if user is None:
        raise HTTPException(status_code=401, detail="로그인이 필요해요.")
    return user

def admin_host_only(request: Request):
    """관리자 API는 정해진 주소(ADMIN_HOSTS, k8s에선 medi.localhost)로 온 요청만 받아요
    Funnel 주소(○○.ts.net)로 온 요청은 관리자 API가 없는 것처럼 404. ADMIN_HOSTS가 비어 있으면(compose) 다 받아요
    요청 주소는 request.headers.get("host")에 있어요. "medi.localhost:80"처럼 포트가 붙을 수 있어요"""
    if not ADMIN_HOSTS:
        return
    host = request.headers.get("host","").split(":")[0]
    if host not in ADMIN_HOSTS:
        raise HTTPException(status_code=404, detail="Not Found")
    


def require_admin(user: dict = Depends(get_current_user)):
    """관리자 화면(H)용: 로그인했고 role이 admin인 사람만 통과. 아니면 403"""
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="관리자만 볼 수 있어요.")
    return user


def require_health_consent(user: dict = Depends(get_current_user)):
    if not user["agree_health"]:
        raise HTTPException(status_code=403, detail="건강정보 수집에 동의해야 쓸 수 있어요.")
    return user

