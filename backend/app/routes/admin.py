from typing import Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy import text

from ..database import SessionLocal
from ..deps import require_admin

# 관리자 화면 (기능명세 H). 모든 주소가 /api/admin/... 이고, 관리자(role=admin)만 쓸 수 있어요
# 라우터 전체에 require_admin을 걸어서, 새 주소를 추가해도 확인을 빼먹지 않아요
router = APIRouter(prefix="/api/admin", tags=["admin"], dependencies=[Depends(require_admin)])

# 질문 기록 거르기: 화면의 선택 상자와 같은 이름
FILTERS = {
    "all": "TRUE",
    "blocked": "blocked",                 # 차단·안내로 돌린 질문 (위험 신호, 진단 요청 등)
    "unclassified": "question_type IS NULL",  # 분류 못 한 질문 → 사전에 단어를 더할 후보
    "reported": "reported OR feedback = -1",  # 사용자가 신고했거나 "도움 안 됨"
}


@router.get("/chat-logs")
def chat_logs(
    only: Literal["all", "blocked", "unclassified", "reported"] = "all",
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """H-1 질문 기록. 질문은 저장할 때 이미 개인정보 모양을 가려 둬요 (I-7)"""
    where = FILTERS[only]   # 정해진 글자만 넣어요 (사용자 입력을 SQL에 직접 넣지 않아요)
    with SessionLocal() as db:
        total = db.execute(text(f"SELECT count(*) FROM chat_log WHERE {where}")).scalar_one()
        rows = db.execute(
            text(f"""
                SELECT log_id, question, answer, question_type, target_item_seq,
                       blocked, block_reason, feedback, reported, created_at
                FROM chat_log
                WHERE {where}
                ORDER BY log_id DESC
                LIMIT :limit OFFSET :offset
            """),
            {"limit": limit, "offset": offset},
        ).mappings().all()
    return {"total": total, "items": [dict(row) for row in rows]}
