import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session
from ..database import get_db
from ..config import OLLAMA_URL

router = APIRouter(
    prefix="/api",
    tags=["Health"]
)


@router.get("/health")
def health(db: Session = Depends(get_db)):
    result = {}

    # DB: 테이블이 몇 개 있는지 세어 본다
    try:
        count = db.execute(text(
            "SELECT count(*) FROM information_schema.tables WHERE table_schema = 'public'"
        )).scalar()
        result["db"] = f"ok (테이블 {count}개)"
    except Exception as e:
        result["db"] = f"실패: {e}"

    # Ollama: 설치된 모델 목록을 받아 본다
    try:
        res = httpx.get(f"{OLLAMA_URL}/api/tags", timeout=5)
        models = [m["name"] for m in res.json()["models"]]
        result["ollama"] = f"ok ({', '.join(models)})"
    except Exception as e:
        result["ollama"] = f"실패: {e}"

    return result

# ── k8s 상태 검사용 (k8s/backend.yaml의 probe). 사람이 보는 위 /health와 달리 짧고, 실패하면 200이 아니에요 ──

@router.get("/health/live")
def live():
    """살아 있나 (liveness): 서버가 응답만 하면 OK. 아무것도 검사하지 않아요.
    DB나 Ollama를 여기서 보면, 그쪽이 잠깐 멈춰도 k8s가 멀쩡한 백엔드를 계속 다시 켜요"""
    return {"ok": True}


@router.get("/health/ready")
def ready(db: Session = Depends(get_db)):
    """손님 받을 준비가 됐나 (readiness): DB만 봐요. Ollama는 보지 않아요 (AI 없이도 검색·약국·내 약은 돼요, REQ-N-012)"""
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        raise HTTPException(status_code=503, detail="DB에 연결할 수 없어요")
    return {"ok": True}
