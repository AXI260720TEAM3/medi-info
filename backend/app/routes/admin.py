from typing import Literal

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import text

from ..database import SessionLocal
from ..deps import require_admin
from ..services.safety import check_safety
from ..services.synonym import find_symptom

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


# H-2 사전 보기. 원본은 data/dict/*.csv (PR로 고쳐요). 여기서는 지금 DB에 들어 있는 내용을 보여 줘요
# 사전마다 (보여 줄 칸, 정렬 순서). 미리 정한 글자만 SQL에 넣어요
DICTS = {
    "symptom_keyword": ("keyword, category, action, is_active", "category, keyword"),   # 위험 증상 → 119·109·응급실·병원
    "caution_keyword": ("keyword, target", "target, keyword"),                          # 주의 대상 (임부·수유·소아·노인·복용중)
    "synonym": ("word, standard, syn_type", "syn_type, word"),                          # 일상어 → 공식 증상, 오타 → 제품명
    "notice_text": ("code, text, updated_at", "code"),                                  # 고정 문구 (면책 안내 등)
}


@router.get("/dict")
def dict_view():
    """사전 4개를 한 번에. 다 합쳐 250줄 정도라 나눠 받지 않아요"""
    with SessionLocal() as db:
        return {
            name: [dict(row) for row in db.execute(text(f"SELECT {cols} FROM {name} ORDER BY {order}")).mappings()]
            for name, (cols, order) in DICTS.items()
        }


class DictTest(BaseModel):
    question: str = Field(min_length=1, max_length=500)


@router.post("/dict/test")
def dict_test(data: DictTest):
    """H-2 문장 시험기: 질문 하나를 AI 질문(chat)과 같은 사전 검사에 넣어 보고 결과만 돌려줘요
    AI는 부르지 않고, 질문 기록에도 남기지 않아요 (사전에 단어를 더하기 전에 미리 확인하는 용도)
    돌려줄 모양: {"safety": check_safety 결과, "symptom": find_symptom 결과(없으면 None)}"""
    question = data.question

    safety = check_safety(question)
    symptom = find_symptom(question)

    return {"safety": safety, "symptom": symptom}

