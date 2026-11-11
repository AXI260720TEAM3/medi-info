# ============================================================
# 파일명: chat.py
# 역할: AI 채팅 API의 요청 처리 및 전체 기능 연결
#
# 주요 기능
# - POST /api/ask: 질문 접수, 약 선택 및 AI 답변 반환
# - 안전 검사, 질문 분석, 약 검색, 답변 생성 기능 연결
# (관리자 질문 기록은 routes/admin.py: GET /api/admin/chat-logs)
#
# 연관 파일
# - services/chat_common.py: 공통 설정 및 AI 호출
# - services/chat_analysis.py: 질문 의도·위험도·대화 맥락 분석
# - services/chat_answer.py: 공식 정보 기반 답변 생성 및 검증
# - services/chat_drug.py: 일반·전문의약품 검색 및 상세 조회
# ============================================================

from sqlalchemy import text
from ..database import SessionLocal
import re
from typing import Literal
import logging
import time
from concurrent.futures import ThreadPoolExecutor
import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from ..services.chat_common import SOURCE, DRUG_FIELDS, FOLLOWUPS
from ..services.chat_analysis import analyze_question
from ..services.chat_answer import _answer_from_official_info
from ..services.chat_drug import find_chat_drug, get_chat_drug_detail
from ..services.drug_api import search_by_efcy
from ..services.drug_search import search_merged
from ..services.privacy import mask_personal
from ..services.dur_api import check_interaction, get_ingredients
from ..services.query_ai import parse_query
from ..services.search import base_name
from ..deps import get_optional_user
from ..services.my_meds import get_profile
from ..services.safety import check_safety, add_disclaimer
from ..services.synonym import find_symptom

router = APIRouter(prefix="/api", tags=["Chat"])


# ③번 팀원의 안전 사전이 먼저 실행되며, 이 목록은 기존 코드의 긴급 신호 보조 검사만 유지합니다.
EMERGENCY_WORDS = (
    "의식이 없", "의식을 잃", "숨을 못 쉬", "숨이 안 쉬",
    "입술이 파래", "피를 토", "가슴이 조이고 숨이 차", "숨이 막혀",
)

# 생성된 답변의 기계적 1차 검사: 의료적 정확성을 보증하지 않습니다.

# 개인 복용 질문으로 남겨야 하는 말: 사람·상태가 드러나는 정보 (11/11)
PERSONAL_INFO = re.compile(
    r"\d{1,3}\s*(?:살|세|개월|kg|킬로)|임신|임산|수유|모유|젖|아기|애기|아이|어린이|소아|초등|중학|고등|"
    r"아들|딸|엄마|아빠|어머니|아버지|할머니|할아버지|노인|어르신|남편|아내|부모|"
    r"제가|저는|저도|내가|나는|나도|"
    r"먹고\s*있|먹는\s*중|복용\s*중|복용하고|처방|지병|질환|당뇨|고혈압|간\s*(?:질환|이\s*안)|신장|콩팥|"
    r"위염|궤양|천식|알레르기|체중|몸무게|술|음주"
)
# 허락을 묻는 말은 개인 질문 그대로 ("이 약 먹어도 돼요?")
PERMISSION_ASK = re.compile(r"먹어도|복용해도|먹여도|괜찮")

REDIRECT_DRUG_LIMIT = 5
REDIRECT_LIST_NOTE = "효능에 이 증상이 적힌 약의 일부예요. 순서는 추천이 아니에요."
REDIRECT_SEARCH_NOTE = "약 찾기에서 증상이나 약 이름으로 약 정보를 찾아볼 수 있어요."


class ChatTurn(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=700)


class DrugRef(BaseModel):
    """약 하나 (API 계약 1장). item_seq는 글자로 (앞자리 0이 사라지지 않게)"""
    item_seq: str = Field(min_length=1, max_length=20)
    item_name: str = Field(default="", max_length=200)


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=1000)
    # 옛 화면: 약 하나. drugs가 비어 있으면 약 하나짜리 목록으로 바꿔 받아요 (계약 7장 5단계에서 지움)
    drug_name: str | None = None
    item_seq: str | None = None
    history: list[ChatTurn] = Field(default_factory=list, max_length=20)
    # E안 (11/10): 이 대화의 약과 지금 약(●). 목록의 주인은 화면이고, 서버는 저장하지 않아요
    drugs: list[DrugRef] = Field(default_factory=list, max_length=10)
    current_seq: str | None = None


def _find_named_drug(question: str) -> dict:
    """질문에 적힌 약 이름을 코드가 먼저 찾아요 (find_chat_drug: e약은요 → 못 찾으면 허가정보까지).
    AI 서버나 약 정보 서버가 안 되면 '못 찾음'으로 두고 AI 분석 흐름에 맡겨요"""
    try:
        result = find_chat_drug(question)
    except (httpx.HTTPError, ValueError, KeyError):
        return {"status": "none"}
    return result if isinstance(result, dict) else {"status": "none"}


def _mentions(item_name: str | None, question: str) -> bool:
    """질문에 이 약 이름(괄호 앞)이 적혀 있나 (띄어쓰기·대소문자 무시)"""
    name = re.sub(r"\s+", "", base_name(item_name or "")).lower()
    return bool(name) and name in re.sub(r"\s+", "", question).lower()


def _ref(drug: dict) -> dict:
    return {"item_seq": str(drug["item_seq"]), "item_name": drug.get("item_name") or ""}


# ── 함께 먹기 (E안 8번, API 계약 2-3의 4번·4장) ─────────────────────────────
# 판정은 check_interaction(식약처 DUR)만 해요. AI는 부르지 않고, 답 문장은 판정으로 정해진 문장을 써요
# (AI가 판정과 어긋나는 말을 할 일이 없고, 카드에 약 짝마다 이유가 따로 나와요)
TOGETHER_WORDS = re.compile(r"함께|같이|동시에|병용|섞어")
# "타이레놀이랑 판피린큐액", "A와 B", "A, B"처럼 약 이름을 잇는 말 (약 이름이 둘 이상인 질문을 나눠 찾을 때)
NAME_JOINERS = re.compile(r"(?:이랑|랑|하고|와|과)\s+|\s*[,/+]\s*|\s+그리고\s+")
MAX_TOGETHER = 10
TOGETHER_ANSWERS = {
    "block": "함께 먹으면 안 되는 조합이 있어요.",
    "warn": "함께 먹을 때 주의가 필요한 조합이 있어요.",
    "unknown": "일부 약은 공식 자료가 부족해 확인을 끝내지 못했어요.",
    "pass": "식약처 자료에서 확인된 병용금기나 성분 겹침은 없어요. 다만 문제가 없다는 뜻은 아니에요.",
}


def _find_drugs_in_parts(question: str, seqs: list[str]) -> tuple[list[dict], list[str]]:
    """'A랑 B 같이 먹어도 돼요?'를 잇는 말로 나눠 조각마다 약을 찾아요 (조각마다 AI 한 번, 동시에).
    (찾은 약 목록, 같은 이름 제품이 여럿이라 정하지 못한 이름 목록)"""
    parts = [p.strip() for p in NAME_JOINERS.split(question) if len(p.strip()) >= 2][:3]
    if len(parts) < 2:
        return [], []
    with ThreadPoolExecutor(max_workers=len(parts)) as pool:
        results = list(pool.map(_find_named_drug, parts))
    found, unclear = [], []
    for result in results:
        if result.get("status") == "found" and (result.get("drug") or {}).get("item_seq"):
            found.append(_ref(result["drug"]))
        elif result.get("status") == "ambiguous":
            # 후보 중에 이 대화의 약이 있으면 그 약 ("타이레놀" + 목록에 타이레놀정500)
            in_list = [c for c in result.get("candidates") or [] if str(c.get("item_seq")) in seqs]
            if in_list:
                found.append(_ref(in_list[0]))
            elif result.get("name"):
                unclear.append(result["name"])
    return found, unclear


def _together_answer(level: str | None, count: int, unclear: list[str]) -> str:
    text = (
        f"식약처 DUR 자료로 이 대화의 약 {count}개를 짝마다 확인했어요. "
        f"{TOGETHER_ANSWERS.get(level or 'pass', TOGETHER_ANSWERS['pass'])} "
        "약 짝마다 이유를 아래에서 확인하고, 복용 전에 약사와 상의하세요."
    )
    if unclear:
        text += (
            f"\n('{', '.join(unclear)}'은(는) 같은 이름의 제품이 여러 개라 넣지 못했어요. "
            "[+ 약 추가]로 정확한 제품을 담은 뒤 다시 물어봐 주세요.)"
        )
    return text


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

def save_chat_log(question: str, result: dict, level: str, response_ms: int | None = None, check: dict | None = None):
    """check: AI 답변 검증 기록 (chat_answer._answer_from_official_info가 채움). AI를 안 부른 답은 비어 있어요
    막힌 초안은 사용자에게 보내지 않고 여기에만 남겨요. 질문처럼 개인정보 모양은 가리고, 90일 뒤 함께 지워요(privacy.py)"""
    check = check or {}
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
                (question, answer, question_type, target_item_seq, blocked, block_reason, response_ms,
                 check_result, check_reason, retry_reason, rejected_draft, retry_ms)
                VALUES
                (:question, :answer, :question_type, :item_seq, :blocked, :block_reason, :response_ms,
                 :check_result, :check_reason, :retry_reason, :rejected_draft, :retry_ms)
            """),
            {
                "question": mask_personal(question),   # 개인정보 모양은 가려서 저장 (I-7)
                "answer": result["answer"],
                "question_type": question_type,
                "item_seq": result.get("item_seq"),
                "blocked": blocked,
                "block_reason": level if blocked else None,
                "response_ms": response_ms,   # 질문을 받은 때부터 답을 만들 때까지 (관리자 대시보드 H-4)
                "check_result": check.get("check_result"),
                "check_reason": check.get("check_reason"),
                "retry_reason": check.get("retry_reason"),
                "rejected_draft": mask_personal(check["rejected_draft"]) if check.get("rejected_draft") else None,
                "retry_ms": check.get("retry_ms"),
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
def ask(data: AskRequest, user: dict | None = Depends(get_optional_user)):
    started = time.monotonic()
    question = data.question.strip()
    if not question:
        raise HTTPException(status_code=422, detail="질문을 입력해 주세요.")

    # 이 대화의 약 (API 계약 2-1). 옛 화면의 item_seq는 약 하나짜리 목록으로 바꿔요
    drugs = [d.model_dump() for d in data.drugs]
    if not drugs and data.item_seq:
        drugs = [{"item_seq": data.item_seq, "item_name": data.drug_name or ""}]
    seqs = [d["item_seq"] for d in drugs]
    current_seq = data.current_seq if data.current_seq in seqs else None
    if current_seq is None and data.item_seq in seqs:
        current_seq = data.item_seq

    # 응답에 더하는 칸 (API 계약 2-2). 아래에서 약을 정하면서 채워요
    extras = {"current_seq": None, "switched": False, "add_drugs": [], "candidates": None, "interaction": None}

    # 위험 사전은 외부 DB 조회. 실패 시 안전 검사를 건너뛰지 않습니다.
    # 로그인하고 건강정보에 동의한 사람은 내 약 화면에서 고른 프로필(임부·소아·노인)도 안전 검사에 넣습니다.
    try:
        profile = get_profile(user["user_id"]) if user and user["agree_health"] else None
        safety = check_safety(question, profile)
    except Exception as exc:
        raise HTTPException(status_code=503, detail="안전 검사 정보를 확인할 수 없어요.") from exc
    
    level = safety.get("level")

    if level not in ("block", "redirect", "warn", "pass"):
        raise HTTPException(
            status_code=503,
            detail="안전 검사 결과를 확인할 수 없어요."
        )

    # AI 답변 검증 기록: AI를 부를 때만 채워지고, 질문 기록에만 저장해요 (응답에는 넣지 않아요. 막힌 초안이 들어 있어서)
    answer_check: dict = {}

    def reply(*args, **kwargs):
        result = {**make_reply(*args, **kwargs), **extras}
        if result.get("item_seq"):
            result["current_seq"] = result["item_seq"]   # 이번 답의 기준 약이 곧 지금 약(●)

        # 지금 약이 바뀌었으면 첫 줄에 알려요 (사용자가 다른 약 이야기로 착각하지 않게)
        if extras["switched"] and result.get("item_name"):
            result["answer"] = f"이제 {base_name(result['item_name'])}에 대해 답할게요.\n\n{result['answer']}"

        if level == "warn" and safety.get("message"):
            result["answer"] += "\n\n" + safety["message"]

        result["answer"] = add_disclaimer(result["answer"])
        save_chat_log(question, result, level, round((time.monotonic() - started) * 1000), answer_check)
        return result
    
    def emergency_reply(answer: str, source: str | None = None):
        result = {**make_reply(
            answer,
            source=source,
            risk="위험 상황",
        ), **extras}

        try:
            save_chat_log(question, result, "block", round((time.monotonic() - started) * 1000))
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

    if current_seq:
        try:
            selected_drug = get_chat_drug_detail(current_seq)
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
    # 질문 속 약 이름은 코드가 먼저 찾아요 (11/10: 약을 고르지 않으면 AI가 keep을 골라 제품명 질문도 막혔음)
    # find_drug도 AI를 한 번 부르니까, AI 분석과 동시에 시작해서 기다리는 시간을 줄여요
    with ThreadPoolExecutor(max_workers=1) as pool:
        named_future = pool.submit(_find_named_drug, question)
        analysis = analyze_question(
            question,
            history_text,
            current_seq,
            None if current_seq else data.drug_name,
            selected_item_name,
        )
        named = named_future.result()
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

    # 개인 정보가 하나도 없는 복용방법 질문("하루에 몇 번 먹어요?")은 일반 용법 질문으로 봐요 (11/11 결정)
    # AI가 개인 질문으로 분류하면 숫자를 쓸 수 없어서, 공식 용법이 있는데도 "판단하기 어려워요"로 끝났어요
    # 나이·임신·가족·먹는 약·지병·"제가"가 있거나 "먹어도 돼요?"처럼 허락을 묻으면 지금처럼 개인 질문으로 둬요
    if (
        risk == "개인 복용 질문"
        and category == "복용방법"
        and not any(PERSONAL_INFO.search(u) for u in user_utterances)
        and not PERMISSION_ASK.search(question)
    ):
        risk = analysis["risk"] = "일반 질문"
        analysis["action"], analysis["missing"] = "explain", "none"

    # 약 검색/선택 API는 기존 계약 유지; 선택된 약이 있어야 개인별 공식 정보 설명 가능.
    if data.drug_name and not data.item_seq and not drugs:
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

    
    # 코드가 질문에서 찾은 약을 AI의 keep/switch보다 먼저 써요 (API 계약 2-3)
    target_item_seq = None
    named_status = named.get("status")
    if named_status == "found" and (named.get("drug") or {}).get("item_seq"):
        target_item_seq = str(named["drug"]["item_seq"])
    elif named_status == "ambiguous":
        candidates = named.get("candidates") or []
        # 후보 중에 이 대화의 약이 있으면 그 약 (지금 약이 먼저): ● 타이레놀정500 + "타이레놀 하루 몇 번?"
        in_list = [c for c in candidates if str(c.get("item_seq")) in seqs]
        pick = next((c for c in in_list if str(c["item_seq"]) == current_seq), in_list[0] if in_list else None)
        if pick:
            target_item_seq = str(pick["item_seq"])
        else:
            extras["candidates"] = [_ref(c) for c in candidates]
            result = reply("같은 이름의 약이 여러 개예요. 어느 약인지 골라 주세요.", risk=risk)
            # 옛 화면용 목록 (계약 7장 5단계에서 지움)
            result["total"] = len(candidates)
            result["items"] = candidates
            result["items_note"] = "같은 이름으로 여러 제품이 검색됐어요. 아래 목록에서 정확한 제품을 확인해 주세요."
            return result
    elif named_status == "none" and named.get("name") and not current_seq:
        pass  # 아래에서 안내 (elif 줄이 길어서 나눔)

    # 함께·같이·비교 질문인데 지금 약도 질문에 적었으면, 다른 약 하나로 바꾸지 않아요 (#94 규칙)
    # 찾은 약은 목록에 담기만 해요 (함께 먹기 판정은 8번 작업에서 DUR로)
    if (
        target_item_seq and current_seq and target_item_seq != current_seq
        and re.search(r"함께|같이|동시|병용|비교|차이", question)
        and _mentions(selected_item_name, question)
    ):
        if target_item_seq not in seqs:
            extras["add_drugs"] = [_ref(named.get("drug") or {"item_seq": target_item_seq})]
        target_item_seq = current_seq

    if named_status == "none" and named.get("name") and not current_seq:
        # 약 이름을 적었는데 찾지 못했고, 대신 답할 지금 약도 없음
        return reply(
            "질문에서 정확한 의약품을 찾지 못했어요. 약 이름을 확인하거나 검색에서 제품을 선택해 주세요.",
            risk=risk,
        )

    # 코드가 못 찾았을 때만 AI의 약 유지·변경·확인 판단을 써요
    drug_action = analysis["drug_action"]

    if target_item_seq is None and (drug_action == "clarify" or (
        drug_action == "keep" and not current_seq
    )):
        return reply(
            "어떤 약에 대한 질문인지 확인이 필요해요. "
            "정확한 제품명을 알려주시거나 제품을 선택해 주세요.",
            risk=risk,
        )

    # 기존 약 유지 또는 새로운 약 검색
    if target_item_seq is None and drug_action == "keep":
        target_item_seq = current_seq

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
            extras["candidates"] = [_ref(c) for c in items]
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
        and target_item_seq == str(current_seq)
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

    # 지금 약이 바뀌었으면 알리고, 목록에 없던 약이면 화면이 담게 해요 (API 계약 2-2)
    extras["switched"] = item_seq != current_seq
    if item_seq not in seqs and all(d["item_seq"] != item_seq for d in extras["add_drugs"]):
        extras["add_drugs"] = extras["add_drugs"] + [{"item_seq": item_seq, "item_name": item_name}]

    drug_source = (
        "식품의약품안전처 의약품 제품 허가정보"
        if drug.get("has_easy") is False
        else SOURCE
    )

    # 함께 먹기 질문: 이 대화의 약 + 질문에서 새로 찾은 약을 짝마다 DUR로 판정해 카드로 답해요 (E안 8번)
    # 나이를 되묻는 것보다 먼저 해요. 함께 먹으면 안 되는 조합은 나이와 상관없이 알려야 해서요
    if category == "상호작용" or TOGETHER_WORDS.search(question):
        pool = {d["item_seq"]: d["item_name"] for d in drugs}
        pool.setdefault(item_seq, item_name)
        for added in extras["add_drugs"]:
            pool.setdefault(added["item_seq"], added["item_name"])
        unclear = []
        if NAME_JOINERS.search(question):
            found, unclear = _find_drugs_in_parts(question, seqs)
            for ref in found:
                if ref["item_seq"] not in pool and len(pool) < MAX_TOGETHER:
                    pool[ref["item_seq"]] = ref["item_name"]
                    if ref["item_seq"] not in seqs:
                        extras["add_drugs"] = extras["add_drugs"] + [ref]
        if len(pool) >= 2:
            try:
                # 내 약 점검과 같은 규칙: 소아 프로필이면 성인 최대 용량 문장을 빼요
                results = check_interaction(list(pool)[:MAX_TOGETHER], show_max_dose=profile != "소아")
            except httpx.HTTPError as exc:
                raise HTTPException(status_code=503, detail="약 정보 서버가 응답하지 않아요.") from exc
            for result in results:
                result["item_name_a"] = pool[result["item_seq_a"]]
                result["item_name_b"] = pool[result["item_seq_b"]]
            level = results[0]["level"] if results else None
            extras["interaction"] = {"level": level, "results": results}
            extras["switched"] = False   # 약 하나가 아니라 짝을 판정한 답이라 "이제 ○○에 대해…"를 붙이지 않아요
            return reply(
                _together_answer(level, min(len(pool), MAX_TOGETHER), unclear),
                item_seq, item_name, "식품의약품안전처 DUR", risk, "상호작용",
            )

    if risk == "개인 복용 질문" and analysis["action"] == "clarify":
        return reply(
            FOLLOWUPS[analysis["missing"]], item_seq, item_name, "대화 안내", risk,
            category if category != "기타" else None,
        )

    # 약이 하나뿐인 개인 병용 질문: DUR 대조 없이 AI가 판단하지 않아요 (#94)
    if risk == "개인 복용 질문" and category == "상호작용":
        return reply(
            "함께 먹을 약을 하나 더 담아 주시면 식약처 DUR 자료로 짝마다 확인해 드릴게요. "
            "질문에 두 약 이름을 함께 쓰거나 [+ 약 추가]로 담을 수 있어요. "
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
        question, analysis["resolved_question"], history_text, drug, risk, category, check=answer_check,
    )
    return reply(answer, item_seq, item_name, drug_source, risk, category)
