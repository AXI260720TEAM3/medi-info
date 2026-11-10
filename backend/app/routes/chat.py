# ============================================================
# 파일명: chat.py
# 역할: AI 채팅 API의 요청 처리 및 전체 기능 연결
#
# 주요 기능
# - POST /api/ask: 질문 접수, 약 선택 및 AI 답변 반환
# - GET /api/admin/chat-logs: 관리자 질문 기록 조회
# - 안전 검사, 질문 분석, 약 검색, 답변 생성 기능 연결
#
# 연관 파일
# - services/chat_common.py: 공통 설정 및 AI 호출
# - services/chat_analysis.py: 질문 의도·위험도·대화 맥락 분석
# - services/chat_answer.py: 공식 정보 기반 답변 생성 및 검증
# - services/chat_drug.py: 일반·전문의약품 검색 및 상세 조회
# ============================================================

import logging
import re
from typing import Literal

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import text

from ..database import SessionLocal
from ..deps import get_current_user

from ..services.chat_common import SOURCE, DRUG_FIELDS, FOLLOWUPS
from ..services.chat_analysis import analyze_question
from ..services.chat_answer import _answer_from_official_info
from ..services.chat_drug import find_chat_drug, get_chat_drug_detail

from ..services.drug_api import search_by_efcy
from ..services.drug_search import search_merged
from ..services.dur_api import get_ingredients
from ..services.query_ai import parse_query
from ..services.synonym import find_symptom

from ..services.privacy import mask_personal
from ..services.safety import check_safety, add_disclaimer

router = APIRouter(prefix="/api", tags=["Chat"])

# ③번 팀원의 안전 사전이 먼저 실행되며, 이 목록은 기존 코드의 긴급 신호 보조 검사만 유지합니다.
EMERGENCY_WORDS = (
    "의식이 없", "의식을 잃", "숨을 못 쉬", "숨이 안 쉬",
    "입술이 파래", "피를 토", "가슴이 조이고 숨이 차", "숨이 막혀",
)

REDIRECT_DRUG_LIMIT = 5
REDIRECT_LIST_NOTE = "효능에 이 증상이 적힌 약의 일부예요. 순서는 추천이 아니에요."
REDIRECT_SEARCH_NOTE = "약 찾기에서 증상이나 약 이름으로 약 정보를 찾아볼 수 있어요."


class ChatTurn(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=700)


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=1000)
    drug_name: str | None = None
    item_seq: str | None = None
    history: list[ChatTurn] = Field(default_factory=list, max_length=20)


def recent_history(history: list[ChatTurn]) -> str:
    """최근 6개 메시지(최대 3회 왕복). 클라이언트가 보내야 기억합니다."""
    if not history:
        return "이전 대화 없음"
    return "\n".join(
        f"{'사용자' if turn.role == 'user' else 'AI'}: {turn.content}"
        for turn in history[-6:]
    )

def has_emergency_signal(question: str) -> bool:
    if any(word in question for word in EMERGENCY_WORDS):
        return True
    return bool(
        re.search(r"호흡곤란|경련", question)
        and re.search(r"지금|갑자기|발생|생겼|있어요|왔어|하고 있어|중이야|시작", question)
    )

def make_reply(
    answer: str,
    item_seq: str | None = None,
    item_name: str | None = None,
    source: str | None = None,
    risk: str | None = None,
    category: str | None = None,
) -> dict:
    """기존 answer/item_seq/item_name/source/risk/category API 형태 유지."""
    result = {"answer": answer}
    if item_seq is not None:
        result["item_seq"] = item_seq
    if item_name is not None:
        result["item_name"] = item_name
    if source is not None:
        result["source"] = source
    if risk is not None:
        result["risk"] = risk
    if category is not None:
        result["category"] = category
    return result

def save_chat_log(question: str, result: dict, level: str):
    blocked = level in ("block", "redirect") or result.get("risk") == "위험 상황"

    if blocked:
        question_type = "차단"
    elif result.get("category") == "상호작용":
        question_type = "함께먹기"
    elif result.get("item_seq"):
        question_type = "약정보"
    else:
        question_type = None

    with SessionLocal() as db:
        db.execute(
            text("""
                INSERT INTO chat_log
                (question, answer, question_type, target_item_seq, blocked, block_reason)
                VALUES
                (:question, :answer, :question_type, :item_seq, :blocked, :block_reason)
            """),
            {
                "question": mask_personal(question),   # 개인정보 모양은 가려서 저장 (I-7)
                "answer": result["answer"],
                "question_type": question_type,
                "item_seq": result.get("item_seq"),
                "blocked": blocked,
                "block_reason": level if blocked else None,
            },
        )
        db.commit()

def redirect_drugs(question: str) -> list[dict]:
    """추천 요청의 증상에 쓰는 약 목록. 조회에 실패해도 안내 문구는 나가야 하므로 빈 목록을 돌려줍니다."""
    try:
        # 약 찾기(/api/drugs/smart)와 같은 순서: 사전에 없는 증상은 AI로 찾습니다.
        symptom = find_symptom(question) or parse_query(question)["symptom"]
        if not symptom:
            return []
        _, items = search_by_efcy(symptom, size=REDIRECT_DRUG_LIMIT)
    except Exception:
        return []
    return [
        {"item_seq": item["item_seq"], "item_name": item["item_name"], "entp_name": item["entp_name"]}
        for item in items
    ]

@router.post("/ask")
def ask(data: AskRequest):
    question = data.question.strip()
    if not question:
        raise HTTPException(status_code=422, detail="질문을 입력해 주세요.")

    # 위험 사전은 외부 DB 조회. 실패 시 안전 검사를 건너뛰지 않습니다.
    try:
        safety = check_safety(question)
    except Exception as exc:
        raise HTTPException(status_code=503, detail="안전 검사 정보를 확인할 수 없어요.") from exc
    
    level = safety.get("level")

    if level not in ("block", "redirect", "warn", "pass"):
        raise HTTPException(
            status_code=503,
            detail="안전 검사 결과를 확인할 수 없어요."
        )

    def reply(*args, **kwargs):
        result = make_reply(*args, **kwargs)

        if level == "warn" and safety.get("message"):
            result["answer"] += "\n\n" + safety["message"]

        result["answer"] = add_disclaimer(result["answer"])
        save_chat_log(question, result, level)
        return result
    
    def emergency_reply(answer: str, source: str | None = None):
        result = make_reply(
            answer,
            source=source,
            risk="위험 상황",
        )

        try:
            save_chat_log(question, result, "block")
        except Exception:
            logging.exception("응급 질문 기록 저장 실패")

        return result

    # 응급 안내는 DB 기록에 실패해도 반환하며, add_disclaimer를 호출하지 않습니다.
    if level == "block":
        return emergency_reply(
            safety.get("message") or "안전 검사 결과를 확인해 주세요.",
            source="안전 사전",
        )

    if level == "redirect":
        result = reply(
            safety.get("message") or "안전 검사 결과를 확인해 주세요.",
            source="안전 사전",
            risk="일반 질문",
        )
        # matched는 [추천 표현, 주의 대상...]입니다. 임신·어린이 등 주의 대상에게는 약 목록을 보여 주지 않습니다.
        result["items"] = [] if safety["matched"][1:] else redirect_drugs(question)
        result["items_note"] = REDIRECT_LIST_NOTE if result["items"] else REDIRECT_SEARCH_NOTE
        return result

    if has_emergency_signal(question):
        return emergency_reply(
            "응급 상황이 의심됩니다. 즉시 119에 연락하거나 응급 진료를 받으세요.",
        )

    # 현재 선택된 약의 정보를 확인해 약 변경 판단에 활용
    selected_drug = None
    selected_item_name = None

    if data.item_seq:
        try:
            selected_drug = get_chat_drug_detail(data.item_seq)
        except httpx.HTTPError as exc:
            raise HTTPException(
                status_code=503,
                detail="약 정보 서버가 응답하지 않아요."
            ) from exc

        if selected_drug is None:
            raise HTTPException(
                status_code=404,
                detail="해당 약을 찾을 수 없어요."
            )

        if not isinstance(selected_drug, dict):
            raise HTTPException(
                status_code=503,
                detail="약 정보 형식을 확인할 수 없어요."
            )

        selected_item_name = selected_drug.get("item_name")

    history_text = recent_history(data.history)
    analysis = analyze_question(
        question,
        history_text,
        data.item_seq,
        data.drug_name,
        selected_item_name,
    )
    risk, category = analysis["risk"], analysis["category"]
    if risk == "위험 상황":
        return emergency_reply(
            "과다복용 또는 응급 상황이 의심되면 증상을 기다리지 말고 즉시 119나 응급의료기관에 연락하세요. "
            "복용한 약과 양·시각을 의료진에게 알려주세요.",
        )
    # AI가 사용자 발언에 없는 나이를 만들어냈는지 확인
    user_utterances = [question] + [
        turn.content
        for turn in data.history[-6:]
        if turn.role == "user"
    ]

    age_pattern = r"(?<!\d)(\d{1,3})\s*(?:세|살)(?!\d)"

    stated_ages = {
        int(age)
        for utterance in user_utterances
        for age in re.findall(age_pattern, utterance)
    }

    resolved_ages = {
        int(age)
        for age in re.findall(age_pattern, analysis["resolved_question"])
    }

    if resolved_ages - stated_ages:
        analysis["resolved_question"] = question

        if risk == "개인 복용 질문":
            analysis["action"] = "clarify"
            analysis["missing"] = "age"

    # 약 검색/선택 API는 기존 계약 유지; 선택된 약이 있어야 개인별 공식 정보 설명 가능.
    if data.drug_name and not data.item_seq:
        try:
            total, items = search_merged(data.drug_name)
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=503, detail="약 정보 서버가 응답하지 않아요.") from exc
        
        result = reply(
            "검색된 약 중 정확한 제품을 선택해 주세요.",
            risk=risk,
        )
        result["total"] = total
        result["items"] = items
        return result

    
    # 약 유지·변경·확인 필요 여부 결정
    drug_action = analysis["drug_action"]

    # AI가 약 이름을 일부만 추출했을 때도
    # 현재 질문에 명시된 정확한 제품명을 공식 검색 결과로 재확인
    if drug_action in ("keep", "clarify", "switch"):
        if drug_action == "switch":
            extracted_name = analysis["new_drug_name"]
        else:
            parsed = parse_query(question)
            extracted_name = (
                parsed.get("drug_name")
                if isinstance(parsed, dict)
                else None
            )

        if isinstance(extracted_name, str):
            extracted_name = extracted_name.strip()
            compact_question = re.sub(r"\s+", "", question).lower()
            compact_name = re.sub(r"\s+", "", extracted_name).lower()

            if compact_name and compact_name in compact_question:
                try:
                    _, products = search_merged(
                        extracted_name, page=1, size=50
                    )
                except httpx.HTTPError as exc:
                    raise HTTPException(
                        status_code=503,
                        detail="약 정보 서버가 응답하지 않아요."
                    ) from exc

                matches = []
                for product in products:
                    base_name = str(
                        product.get("item_name") or ""
                    ).split("(")[0].strip()

                    compact_base = re.sub(
                        r"\s+", "", base_name
                    ).lower()

                    if compact_base and compact_base in compact_question:
                        matches.append(product)

                # 여러 약이 등장하거나 병용·비교 질문이면
                # AI의 모호성 판단을 임의로 덮어쓰지 않음
                multiple_drug_question = bool(
                    re.search(r"함께|같이|동시|병용|비교|차이", question)
                )

                selected_base = re.sub(
                    r"\s+", "",
                    str(selected_item_name or "").split("(")[0]
                ).lower()

                mentions_selected = bool(
                    selected_base and selected_base in compact_question
                )

                if (
                    len(matches) == 1
                    and not multiple_drug_question
                    and not (
                        mentions_selected
                        and str(matches[0]["item_seq"])
                        != str(data.item_seq)
                    )
                ):
                    verified = matches[0]
                    verified_seq = str(verified["item_seq"])

                    if verified_seq == str(data.item_seq):
                        drug_action = "keep"
                    else:
                        drug_action = "switch"
                        analysis["new_drug_name"] = (
                            verified["item_name"].split("(")[0].strip()
                        )

    if drug_action == "clarify" or (
        drug_action == "keep" and not data.item_seq
    ):
        return reply(
            "어떤 약에 대한 질문인지 확인이 필요해요. "
            "정확한 제품명을 알려주시거나 제품을 선택해 주세요.",
            risk=risk,
        )

    # 기존 약 유지 또는 새로운 약 검색
    target_item_seq = (
        data.item_seq if drug_action == "keep" else None
    )

    if not target_item_seq:
        try:
            search_result = find_chat_drug(
                analysis["new_drug_name"]
            )
        except httpx.HTTPError as exc:
            raise HTTPException(
                status_code=503,
                detail="약 정보 서버가 응답하지 않아요.",
            ) from exc

        if not isinstance(search_result, dict):
            raise HTTPException(
                status_code=503,
                detail="약 검색 결과를 확인할 수 없어요.",
            )

        status = search_result.get("status")

        if status == "found":
            found_drug = search_result.get("drug") or {}
            found_item_seq = found_drug.get("item_seq")

            if not found_item_seq:
                raise HTTPException(
                    status_code=503,
                    detail="검색된 약의 품목번호를 확인할 수 없어요.",
                )

            target_item_seq = str(found_item_seq)

        elif status == "ambiguous":
            items = search_result.get("candidates") or []
            result = reply(
                "검색된 약 중 정확한 제품을 선택해 주세요.",
                risk=risk,
            )
            result["total"] = len(items)
            result["items"] = items
            result["items_note"] = (
                "검색된 제품이 1개예요. 아래 제품이 맞는지 확인해 주세요."
                if len(items) == 1
                else "같은 이름으로 여러 제품이 검색됐어요. 아래 목록에서 정확한 제품을 확인해 주세요."
            )
            return result

        elif status == "none":
            return reply(
                "질문에서 정확한 의약품을 찾지 못했어요. 약 이름을 확인하거나 검색에서 제품을 선택해 주세요.",
                risk=risk,
            )

        else:
            raise HTTPException(
                status_code=503,
                detail="약 검색 상태를 확인할 수 없어요.",
            )

    # 최종 선택된 약의 공식 정보 확인
    if (
        selected_drug is not None
        and target_item_seq == str(data.item_seq)
    ):
        drug = selected_drug
    else:
        try:
            drug = get_chat_drug_detail(target_item_seq)
        except httpx.HTTPError as exc:
            raise HTTPException(
                status_code=503,
                detail="약 정보 서버가 응답하지 않아요."
            ) from exc

    if drug is None:
        raise HTTPException(
            status_code=404,
            detail="해당 약을 찾을 수 없어요."
        )

    if not isinstance(drug, dict):
        raise HTTPException(
            status_code=503,
            detail="약 정보 형식을 확인할 수 없어요."
        )

    item_seq = str(drug.get("item_seq") or target_item_seq)
    item_name = drug.get("item_name") or "선택된 의약품"
    drug = {**drug, "item_seq": item_seq, "item_name": item_name}

    drug_source=(
        "식품의약품안전처 의약품 제품 허가정보"
        if drug.get("has_easy")is False
        else SOURCE
    )

    if risk == "개인 복용 질문" and analysis["action"] == "clarify":
        return reply(
            FOLLOWUPS[analysis["missing"]], item_seq, item_name, "대화 안내", risk,
            category if category != "기타" else None,
        )

    # 개인별 약물 병용 질문은 DUR 대조 없이 AI가 판단하지 않도록 차단
    if risk == "개인 복용 질문" and category == "상호작용":
        return reply(
            "질문하신 약들을 함께 복용해도 되는지는 "
            "현재 확인한 정보만으로 판단할 수 없어요. "
            "복용 여부나 처방을 임의로 변경하지 말고 "
            "의사 또는 약사에게 정확한 약 이름을 알려 확인해 주세요.",
            item_seq,
            item_name,
            "대화 안내",
            risk,
            category,
        )

    # 성분 질문은 기존 공식 성분 API로 조회
    if category == "성분":
        try:
            ingredients = get_ingredients(item_seq)
        except httpx.HTTPError as exc:
            raise HTTPException(
                status_code=503,
                detail="성분 정보 서버가 응답하지 않아요.",
            ) from exc

        names = [
            item["MTRAL_NM"].strip()
            for item in ingredients
            if item.get("MTRAL_NM")
        ]
        names = list(dict.fromkeys(names))

        if not names:
            return reply(
                "공식 자료에서 이 약의 성분 정보를 확인할 수 없어요. 약사와 상담해 주세요.",
                item_seq, item_name, None, risk, category,
            )

        answer = f"{item_name}의 성분은 {', '.join(names)}입니다."

        if risk == "개인 복용 질문":
            answer += " 이 정보만으로 개인별 복용 가능 여부를 판단할 수 없으므로 의사 또는 약사에게 확인해 주세요."

        return reply(
            answer,
            item_seq,
            item_name,
            "식품의약품안전처 의약품 제품 허가정보",
            risk,
            category,
        )

    if category == "기타":
        if risk == "개인 복용 질문":
            category = "주의사항"  # 공식 안전 관련 자료만 참고하는 보수적 기본값
        else:
            return reply(
                "어떤 약 정보가 궁금한지 조금 더 구체적으로 알려주세요.",
                item_seq, item_name, drug_source, risk, category,
            )

    if risk == "일반 질문":
        primary = drug.get(DRUG_FIELDS[category])
        if not primary or not str(primary).strip():
            return reply(
                f"현재 조회한 공식 의약품 정보에서 '{category}' 항목을 확인할 수 없어요.",
                item_seq, item_name, drug_source, risk, category,
            )
    else:
        if not any(str(drug.get(DRUG_FIELDS[name]) or "").strip() for name in ("복용방법", "복용 전 경고", "주의사항")):
            return reply(
                "현재 확인한 공식 정보에는 이 질문과 관련된 복용·주의 자료가 부족해요. "
                "개인별 복용 가능 여부는 의사 또는 약사에게 확인해 주세요.",
                item_seq, item_name, drug_source, risk, category,
            )

    answer = _answer_from_official_info(
        question, analysis["resolved_question"], history_text, drug, risk, category,
    )
    return reply(answer, item_seq, item_name, drug_source, risk, category)

@router.get("/admin/chat-logs")
def get_chat_logs(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user: dict = Depends(get_current_user),
):
    if user.get("role") != "admin":
        raise HTTPException(
            status_code=403,
            detail="관리자만 볼 수 있어요."
        )

    with SessionLocal() as db:
        rows = db.execute(
            text("""
                SELECT log_id, question, answer, question_type,
                       target_item_seq, blocked, block_reason, created_at
                FROM chat_log
                ORDER BY log_id DESC
                LIMIT :limit OFFSET :offset
            """),
            {"limit": limit, "offset": offset},
        ).mappings().all()

    return {"items": [dict(row) for row in rows]}