import logging
import time
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from typing import Literal

import httpx

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import text

from ..config import OLLAMA_URL, OPS_TOKEN, OPS_URL
from ..database import SessionLocal
from ..deps import admin_host_only, require_admin
from ..services.safety import check_safety
from ..services.synonym import find_symptom

# 관리자 화면 (기능명세 H). 모든 주소가 /api/admin/... 이고, 관리자(role=admin)만 쓸 수 있어요
# 라우터 전체에 require_admin을 걸어서, 새 주소를 추가해도 확인을 빼먹지 않아요
# 주소 확인을 먼저: Funnel로 온 요청은 로그인 여부와 상관없이 404 (관리자 API가 있다는 것도 알리지 않아요)
router = APIRouter(prefix="/api/admin", tags=["admin"], dependencies=[Depends(admin_host_only), Depends(require_admin)])

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



# H-4 대시보드: 질문 기록(chat_log)으로 본 이용 현황 + 서버 상태
def _ollama_status():
    """AI 모델 서버(Ollama, k8s 밖 WSL)가 살아 있는지. 모델 목록만 물어봐요 (답 만들기는 안 해요)"""
    started = time.monotonic()
    try:
        httpx.get(f"{OLLAMA_URL}/api/tags", timeout=3).raise_for_status()
        return {"ok": True, "ms": round((time.monotonic() - started) * 1000)}
    except httpx.HTTPError:
        return {"ok": False, "ms": None}


def _daily_counts(db, days):
    """최근 days일의 날짜별 질문 수 → {date: (전체, 차단)}. 질문이 없는 날은 빠져 있어도 돼요 (아래에서 0으로 채워요)
    날짜는 한국 시간 기준이에요 (DB는 UTC로 저장)"""
    rows = db.execute(text("""
        SELECT (created_at AT TIME ZONE 'Asia/Seoul')::date AS day,
               count(*) AS total,
               count(*) FILTER (WHERE blocked) AS blocked
        FROM chat_log
        WHERE created_at >= now() - make_interval(days => :days)
        GROUP BY day
    """), {"days": days}).mappings().all()
    return {row["day"]: (row["total"], row["blocked"]) for row in rows}


@router.get("/dashboard")
def dashboard(days: int = Query(7, ge=1, le=90)):
    with SessionLocal() as db:
        counts = _daily_counts(db, days)
        totals = db.execute(text("""
            SELECT count(*) AS questions,
                   count(*) FILTER (WHERE blocked) AS blocked,
                   count(*) FILTER (WHERE question_type IS NULL) AS unclassified,
                   count(*) FILTER (WHERE reported OR feedback = -1) AS reported
            FROM chat_log WHERE created_at >= now() - make_interval(days => :days)
        """), {"days": days}).mappings().one()
        types = db.execute(text("""
            SELECT coalesce(question_type, '분류 못 함') AS type, count(*) AS count
            FROM chat_log WHERE created_at >= now() - make_interval(days => :days)
            GROUP BY 1 ORDER BY 2 DESC
        """), {"days": days}).mappings().all()
        response = db.execute(text("""
            SELECT count(response_ms) AS measured,
                   round(avg(response_ms)) AS avg_ms,
                   round(percentile_cont(0.95) WITHIN GROUP (ORDER BY response_ms)) AS p95_ms
            FROM chat_log
            WHERE created_at >= now() - make_interval(days => :days) AND response_ms IS NOT NULL
              AND NOT blocked   -- 차단은 AI를 안 불러서 빨라요. 섞으면 평균이 실제보다 좋아 보여요
        """), {"days": days}).mappings().one()
        dict_counts = {name: db.execute(text(f"SELECT count(*) FROM {name}")).scalar_one() for name in DICTS}

    today = datetime.now(ZoneInfo("Asia/Seoul")).date()   # 컨테이너 시계는 UTC라서 한국 날짜로
    daily = []
    for i in range(days - 1, -1, -1):   # 오래된 날 → 오늘, 질문이 없는 날은 0
        day = today - timedelta(days=i)
        total, blocked = counts.get(day, (0, 0))
        daily.append({"day": day.isoformat(), "total": total, "blocked": blocked})

    return {
        "days": days,
        "status": {"db": True, "ollama": _ollama_status()},   # DB는 여기까지 왔으면 살아 있어요
        "totals": dict(totals),
        "daily": daily,
        "types": [dict(row) for row in types],
        "response": {k: (int(v) if v is not None else None) for k, v in response.items()},
        "dict_counts": dict_counts,
    }


# H-5 운영: k8s 권한은 백엔드가 아니라 운영 API(ops 파드)에 있어요. 백엔드는 관리자 확인 뒤 넘겨주기만 해요
def _ops(method, path):
    if not OPS_URL:
        raise HTTPException(status_code=503, detail="운영 탭은 k8s에서 실행할 때만 쓸 수 있어요. 지금은 compose예요.")
    try:
        res = httpx.request(method, f"{OPS_URL}{path}", headers={"X-Ops-Token": OPS_TOKEN}, timeout=10)
    except httpx.HTTPError:
        raise HTTPException(status_code=503, detail="운영 API에 연결하지 못했어요. ops 파드를 확인해 주세요.")
    body = res.json() if res.headers.get("content-type", "").startswith("application/json") else {}
    if res.status_code >= 400:
        raise HTTPException(status_code=502 if res.status_code >= 500 else res.status_code,
                            detail=body.get("detail") or "운영 API가 거절했어요.")
    return body


@router.get("/ops/status")
def ops_status():
    return _ops("GET", "/status")


@router.post("/ops/restart/{name}")
def ops_restart(name: Literal["backend", "web"], user: dict = Depends(require_admin)):
    logging.warning("관리자 %s: %s 다시 시작", user["login_id"], name)   # 누가 했는지 남겨요
    return _ops("POST", f"/restart/{name}")


@router.post("/ops/dict-reload")
def ops_dict_reload(user: dict = Depends(require_admin)):
    logging.warning("관리자 %s: 사전 다시 적재", user["login_id"])
    return _ops("POST", "/dict-reload")
