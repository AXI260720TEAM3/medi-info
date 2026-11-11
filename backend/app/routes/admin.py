import logging
import time
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from typing import Literal

import httpx

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import text

from ..config import OLLAMA_NUM_CTX, OLLAMA_URL, OPS_TOKEN, OPS_URL
from ..database import SessionLocal
from ..deps import admin_host_only, require_admin
from ..services.chat_common import MODEL
from ..services.safety import check_safety
from ..services.synonym import find_symptom

# 관리자 화면 (기능명세 H). 모든 주소가 /api/admin/... 이고, 관리자(role=admin)만 쓸 수 있어요
# 라우터 전체에 require_admin을 걸어서, 새 주소를 추가해도 확인을 빼먹지 않아요
# 주소 확인을 먼저: Funnel로 온 요청은 로그인 여부와 상관없이 404 (관리자 API가 있다는 것도 알리지 않아요)
router = APIRouter(prefix="/api/admin", tags=["admin"], dependencies=[Depends(admin_host_only), Depends(require_admin)])

# 질문 기록 거르기: 화면의 결과 칩과 같은 이름. 정해진 글자만 SQL에 넣어요 (사용자 입력은 :q 같은 값으로만)
FILTERS = {
    "all": "TRUE",
    "blocked": "blocked",                             # 차단·안내 (위험 신호 119, 추천·진단 요청 거절)
    "ask_drug": "question_type = '약확인'",            # 어느 약인지 되물음
    "check_failed": "check_reason IS NOT NULL",       # AI 첫 답이 검증에 걸림 (다시 써서 통과 또는 대체)
    "reported": "(reported OR feedback = -1)",        # 사용자가 신고했거나 "도움 안 됨"
    "interaction": "question_type = '함께먹기'",       # 함께 먹기 판정 (DUR)
    "unclassified": "question_type IS NULL",          # 그 밖에 종류를 못 정한 답
}


@router.get("/chat-logs")
def chat_logs(
    only: Literal["all", "blocked", "ask_drug", "check_failed", "reported", "interaction", "unclassified"] = "all",
    q: str = Query("", max_length=100),
    days: int = Query(7, ge=1, le=90),   # 화면은 7·30·90 (Literal[7, 30, 90]은 주소의 "30"을 숫자로 못 바꿔서 422)
    hide_test: bool = True,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """H-1 질문 기록 표. 질문은 저장할 때 이미 개인정보 모양을 가려 둬요 (I-7)
    칩마다 건수(counts)는 기간·검색·시험 빼기를 적용한 범위에서 세요"""
    base = ["created_at >= now() - make_interval(days => :days)"]
    params = {"days": days, "limit": limit, "offset": offset}
    if hide_test:
        base.append("NOT is_test")
    if q.strip():
        # % _ 는 LIKE에서 특별한 글자라 그대로 찾도록 막아요
        params["q"] = "%" + q.strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
        base.append("(question ILIKE :q OR item_name ILIKE :q)")
    base_where = " AND ".join(base)
    counts_sql = ", ".join(f"count(*) FILTER (WHERE {cond}) AS {name}" for name, cond in FILTERS.items())
    with SessionLocal() as db:
        counts = db.execute(text(f"SELECT {counts_sql} FROM chat_log WHERE {base_where}"), params).mappings().one()
        hidden = db.execute(text(
            "SELECT count(*) FROM chat_log WHERE is_test AND created_at >= now() - make_interval(days => :days)"
        ), {"days": days}).scalar_one() if hide_test else 0
        rows = db.execute(
            text(f"""
                SELECT log_id, question, answer, question_type, target_item_seq, item_name,
                       blocked, block_reason, feedback, reported, response_ms, created_at,
                       check_result, check_reason, retry_ms, is_test
                FROM chat_log
                WHERE {base_where} AND {FILTERS[only]}
                ORDER BY log_id DESC
                LIMIT :limit OFFSET :offset
            """),
            params,
        ).mappings().all()
    return {
        "total": counts[only],
        "counts": dict(counts),
        "hidden_test": hidden,
        "items": [{**row, "created_at": row["created_at"].isoformat()} for row in rows],
    }


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



# 서버 상태: 대시보드 통계와 따로 불러요. DB가 죽어도 이 주소는 "DB 응답 없음"을 돌려줘요
# (예전에는 통계 쿼리가 성공해야 화면이 떠서, DB가 죽으면 상태 대신 오류만 보였어요)
# 판정: ok(정상) · warn(돌긴 하지만 느리거나 설정이 어긋남) · down(그 기능이 실패해요)
def _ms(started):
    return round((time.monotonic() - started) * 1000)


def _db_health():
    started = time.monotonic()
    try:
        with SessionLocal() as db:
            db.execute(text("SELECT 1"))
            counts = {name: db.execute(text(f"SELECT count(*) FROM {name}")).scalar_one() for name in DICTS}
    except Exception as exc:   # 연결 실패·시간 초과 등 무엇이든 "DB 응답 없음"으로 보여 줘요
        return {"state": "down", "detail": f"DB에 연결하지 못했어요 ({type(exc).__name__})"}, None
    return {"state": "ok", "ms": _ms(started)}, counts


def _dict_health(counts):
    if counts is None:
        return {"state": "down", "detail": "DB가 응답하지 않아 확인하지 못했어요"}
    # 고정 문구가 없으면 AI 답이 500, 위험 증상이 없으면 119 안내가 빠져요 → 둘은 0이면 down
    empty = [name for name in ("notice_text", "symptom_keyword") if counts[name] == 0]
    if empty:
        return {"state": "down", "detail": f"비어 있어요: {', '.join(empty)} → 운영 탭에서 사전 다시 적재", "counts": counts}
    return {"state": "ok", "counts": counts}


def _ollama_health():
    """AI 모델 서버(Ollama, k8s 밖 WSL). 목록만 물어보고 답 만들기는 안 해요
    /api/ps로 모델이 GPU에 올라가 있는지, 문맥 길이가 백엔드 설정(OLLAMA_NUM_CTX)과 같은지도 봐요
    (다르면 질문마다 모델을 다시 올려서 몇 초씩 느려져요. 11/11에 10분에 34번 다시 올린 적 있음)"""
    started = time.monotonic()
    try:
        tags = httpx.get(f"{OLLAMA_URL}/api/tags", timeout=3).raise_for_status().json()
        ps = httpx.get(f"{OLLAMA_URL}/api/ps", timeout=3).raise_for_status().json()
    except (httpx.HTTPError, ValueError):
        return {"state": "down", "detail": "응답 없음. AI 질문이 503으로 실패해요. WSL에서 Ollama가 켜져 있는지 확인해 주세요."}
    ms = _ms(started)
    if MODEL not in {m["name"] for m in tags.get("models", [])}:
        return {"state": "down", "ms": ms, "detail": f"모델 {MODEL}이 설치되어 있지 않아요 (ollama pull)"}
    loaded = next((m for m in ps.get("models", []) if m["name"] == MODEL), None)
    if loaded is None:
        # 5분 동안 안 쓰면 Ollama가 내려요. 다음 질문이 모델을 올리느라 10초쯤 더 걸릴 뿐 고장은 아니에요
        return {"state": "ok", "ms": ms, "model": MODEL, "loaded": False}
    gpu = round(loaded["size_vram"] / loaded["size"] * 100) if loaded.get("size") else None
    ctx = loaded.get("context_length")
    model = {"state": "ok", "ms": ms, "model": MODEL, "loaded": True, "gpu_pct": gpu, "ctx": ctx,
             "size_gb": round(loaded["size"] / 1e9, 1)}
    problems = []
    if gpu is not None and gpu < 100:
        problems.append(f"모델의 {100 - gpu}%가 GPU에 안 들어가 CPU로 돌아요 (느려짐)")
    if ctx and ctx != OLLAMA_NUM_CTX:
        problems.append(f"문맥 길이가 Ollama {ctx}, 백엔드 {OLLAMA_NUM_CTX}로 달라요 (질문마다 모델을 다시 올려요)")
    if problems:
        model.update(state="warn", detail=" · ".join(problems))
    return model


@router.get("/health")
def health():
    db, counts = _db_health()
    return {"db": db, "ollama": _ollama_health(), "dict": _dict_health(counts)}


# H-4 대시보드: 질문 기록(chat_log)으로 본 이용 현황


def _daily_counts(db, days):
    """최근 days일의 날짜별 질문 수 → {date: (전체, 차단)}. 질문이 없는 날은 빠져 있어도 돼요 (아래에서 0으로 채워요)
    날짜는 한국 시간 기준이에요 (DB는 UTC로 저장)"""
    rows = db.execute(text("""
        SELECT (created_at AT TIME ZONE 'Asia/Seoul')::date AS day,
               count(*) AS total,
               count(*) FILTER (WHERE blocked) AS blocked
        FROM chat_log
        WHERE created_at >= now() - make_interval(days => :days) AND NOT is_test
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
                   count(*) FILTER (WHERE question_type = '약확인') AS ask_drug,
                   count(*) FILTER (WHERE question_type IS NULL) AS unclassified,
                   count(*) FILTER (WHERE reported OR feedback = -1) AS reported
            FROM chat_log WHERE created_at >= now() - make_interval(days => :days) AND NOT is_test
        """), {"days": days}).mappings().one()
        types = db.execute(text("""
            SELECT coalesce(question_type, '분류 못 함') AS type, count(*) AS count
            FROM chat_log WHERE created_at >= now() - make_interval(days => :days) AND NOT is_test
            GROUP BY 1 ORDER BY 2 DESC
        """), {"days": days}).mappings().all()
        response = db.execute(text("""
            SELECT count(response_ms) AS measured,
                   round(avg(response_ms)) AS avg_ms,
                   round(percentile_cont(0.95) WITHIN GROUP (ORDER BY response_ms)) AS p95_ms
            FROM chat_log
            WHERE created_at >= now() - make_interval(days => :days) AND NOT is_test AND response_ms IS NOT NULL
              AND NOT blocked   -- 차단은 AI를 안 불러서 빨라요. 섞으면 평균이 실제보다 좋아 보여요
        """), {"days": days}).mappings().one()

    today = datetime.now(ZoneInfo("Asia/Seoul")).date()   # 컨테이너 시계는 UTC라서 한국 날짜로
    daily = []
    for i in range(days - 1, -1, -1):   # 오래된 날 → 오늘, 질문이 없는 날은 0
        day = today - timedelta(days=i)
        total, blocked = counts.get(day, (0, 0))
        daily.append({"day": day.isoformat(), "total": total, "blocked": blocked})

    return {
        "days": days,
        "totals": dict(totals),
        "daily": daily,
        "types": [dict(row) for row in types],
        "response": {k: (int(v) if v is not None else None) for k, v in response.items()},
    }


# AI 답변 검증: chat_answer.py가 AI 글을 내보내기 전에 검사한 결과 (db/init/04_answer_check.sql)
# check_result가 NULL인 질문은 AI를 부르지 않은 답이에요 (위험 신호 차단, 함께 먹기 판정, 자료 없음 안내 등)
@router.get("/answer-checks")
def answer_checks(days: int = Query(7, ge=1, le=90)):
    period = {"days": days}
    with SessionLocal() as db:
        summary = db.execute(text("""
            SELECT count(check_result) AS ai,
                   count(*) FILTER (WHERE check_result = 'pass') AS pass,
                   count(*) FILTER (WHERE check_result = 'retry_pass') AS retry_pass,
                   count(*) FILTER (WHERE check_result = 'fallback') AS fallback,
                   count(*) FILTER (WHERE check_result IS NULL) AS no_ai,
                   round(avg(retry_ms)) AS retry_ms_avg
            FROM chat_log WHERE created_at >= now() - make_interval(days => :days) AND NOT is_test
        """), period).mappings().one()
        reasons = db.execute(text("""
            SELECT check_reason AS reason, count(*) AS n,
                   count(*) FILTER (WHERE check_result = 'retry_pass') AS saved,
                   count(*) FILTER (WHERE check_result = 'fallback') AS replaced
            FROM chat_log
            WHERE created_at >= now() - make_interval(days => :days) AND NOT is_test AND check_reason IS NOT NULL
            GROUP BY 1 ORDER BY 2 DESC, 1
        """), period).mappings().all()
        recent = db.execute(text("""
            SELECT log_id, question, check_reason, check_result, created_at
            FROM chat_log
            WHERE created_at >= now() - make_interval(days => :days) AND NOT is_test AND check_reason IS NOT NULL
            ORDER BY created_at DESC LIMIT 5
        """), period).mappings().all()
    return {
        "days": days,
        "summary": {k: (int(v) if v is not None else None) for k, v in summary.items()},
        "reasons": [dict(r) for r in reasons],
        "recent": [{**r, "created_at": r["created_at"].isoformat()} for r in recent],
    }


@router.get("/answer-checks/{log_id}")
def answer_check_detail(log_id: int):
    """질문 하나의 검증 과정: 질문 → 막힌 첫 초안과 사유 → (다시 쓴 답의 사유) → 사용자에게 간 답"""
    with SessionLocal() as db:
        row = db.execute(text("""
            SELECT log_id, question, answer, question_type, target_item_seq, response_ms, created_at,
                   check_result, check_reason, retry_reason, rejected_draft, retry_ms
            FROM chat_log WHERE log_id = :id
        """), {"id": log_id}).mappings().first()
    if row is None:
        raise HTTPException(status_code=404, detail="질문 기록을 찾을 수 없어요. 보관 기간(90일)이 지나 지워졌을 수 있어요.")
    return {**row, "created_at": row["created_at"].isoformat()}


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


@router.get("/ops/resources")
def ops_resources():
    return _ops("GET", "/resources")


@router.post("/ops/restart/{name}")
def ops_restart(name: Literal["backend", "web"], user: dict = Depends(require_admin)):
    logging.warning("관리자 %s: %s 다시 시작", user["login_id"], name)   # 누가 했는지 남겨요
    return _ops("POST", f"/restart/{name}")


@router.post("/ops/dict-reload")
def ops_dict_reload(user: dict = Depends(require_admin)):
    logging.warning("관리자 %s: 사전 다시 적재", user["login_id"])
    return _ops("POST", "/dict-reload")


# 백업 파일·예약은 ops가, DB 안의 크기는 DB 계정이 있는 백엔드가 봐요 (ops는 DB 계정이 없어요)
@router.get("/ops/backups")
def ops_backups():
    data = _ops("GET", "/backups")
    with SessionLocal() as db:
        data["db_size_mib"] = round(db.execute(text("SELECT pg_database_size(current_database())")).scalar() / 2**20, 1)
        # n_live_tup는 DB가 넣고 지울 때마다 세어 둔 대략의 행 수예요 (count(*)처럼 표 전체를 읽지 않아요)
        data["tables"] = [{"name": name, "size_mib": round(size / 2**20, 2), "rows": rows} for name, size, rows in db.execute(text(
            """SELECT relname, pg_total_relation_size(relid), n_live_tup FROM pg_stat_user_tables
               WHERE schemaname = 'public' ORDER BY 2 DESC LIMIT 5"""))]
    return data


@router.post("/ops/backup-now")
def ops_backup_now(user: dict = Depends(require_admin)):
    logging.warning("관리자 %s: 지금 백업", user["login_id"])
    return _ops("POST", "/backup-now")


@router.get("/ops/traffic")
def ops_traffic():
    return _ops("GET", "/traffic")


@router.get("/ops/deployments")
def ops_deployments():
    return _ops("GET", "/deployments")
