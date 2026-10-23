import httpx
from fastapi import APIRouter, Depends
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