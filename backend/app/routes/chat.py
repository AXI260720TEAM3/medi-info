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
from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field

from ..services.chat_common import SOURCE, DRUG_FIELDS, FOLLOWUPS
from ..services.chat_analysis import analyze_question
from ..services.chat_answer import _answer_from_official_info
from ..services.chat_drug import find_chat_drug, get_chat_drug_detail
from ..services.drug_api import search_by_efcy
from ..services.drug_search import search_by_ingredient, search_merged
from ..services.privacy import mask_personal
from ..services.dur_api import check_interaction, get_ingredients, profile_cautions
from ..services.query_ai import parse_query
from ..services.search import base_name
from ..deps import get_optional_user
from ..services.my_meds import get_profile
from ..services.safety import CAUTION_MESSAGES, check_safety, add_disclaimer, caution_targets
from ..services.drug_type import (
    DUR_TARGETS, TARGET_NAMES, TYPE_MEANINGS, find_drug_type, type_cautions, type_cautions_answer,
)
from ..services.synonym import common_symptoms, find_symptom

router = APIRouter(prefix="/api", tags=["Chat"])


# 응급(119) 단어는 안전 사전(data/dict/symptom_keyword.csv) 한 곳에서만 관리해요 (11/12)
# 예전에는 여기에 문장 8개가 따로 있었는데, 글자가 그대로 같아야만 잡아서 "가슴이 조이는 느낌이에요"를 놓쳤고
# 관리자 사전 탭에도 안 보였어요. 사전에 없던 것(가슴+조이, 의식+잃, 입술+파래·파랗)을 사전으로 옮겼어요

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
# 먹기 전에 묻는 말과 이미 먹은 말: AI의 '위험 상황'을 그대로 쓸지 정할 때 봐요 (11/12)
ASK_BEFORE_TAKING = re.compile(r"(?:먹어|먹여|복용해|드셔|발라|써|사용해)\s*도\s*(?:돼|되|괜찮|될)")
ALREADY_TAKEN = re.compile(r"먹었|먹은|먹여버|먹였|삼켰|마셨|복용했|복용한|드셨|과다|많이")

REDIRECT_DRUG_LIMIT = 5
REDIRECT_LIST_NOTE = "효능에 이 증상이 적힌 약의 일부예요. 순서는 추천이 아니에요."
REDIRECT_SEARCH_NOTE = "약 찾기에서 증상이나 약 이름으로 약 정보를 찾아볼 수 있어요."
INGREDIENT_PICK_LIMIT = 10
GUIDE_ANSWER = (
    "약에 대해 궁금한 점을 물어봐 주세요. '타이레놀 하루에 몇 번 먹어요?'처럼 약 이름과 함께 물으면 "
    "식약처 공식 자료로 답해 드려요. '머리가 지끈거려요'처럼 증상을 말하면 그 증상에 쓰는 약을 찾아 드리고, "
    "가까운 약국은 위의 [약국] 메뉴에서 찾을 수 있어요."
)
# 약 목록을 보여 줘도 되는 증상: 증상 사전의 흔한 증상 + 감기류 (11/12)
# 그 밖의 증상(흉통·호흡곤란 등)은 약보다 진료가 먼저일 수 있어서 목록 없이 예전처럼 되물어요
# ("가슴이 조이는 느낌이에요"가 '흉통' 약 목록으로 나가던 것을 시험에서 발견)
LISTABLE_SYMPTOMS_EXTRA = {"감기", "코감기", "목감기", "재채기", "비염"}
# 어느 약인지 되묻는 문구 (예전에는 같은 뜻의 문구 4가지가 섞여 나갔어요)
PICK_MESSAGE = "같은 이름의 약이 여러 개예요. 어느 약인지 골라 주세요."
NOT_FOUND_MESSAGE = "질문에서 정확한 의약품을 찾지 못했어요. 약 이름을 확인하거나 검색에서 제품을 선택해 주세요."
WHICH_MESSAGE = "어떤 약에 대한 질문인지 확인이 필요해요. 정확한 제품명을 알려주시거나 제품을 선택해 주세요."
COMPARE_WORDS = re.compile(r"함께|같이|동시|병용|비교|차이")
# 담긴 약을 가리키는 말: "이 약", "그 약", "이거" … ("두통이 약간"·"이 약국"은 아니에요)
DRUG_REFERENCE = re.compile(r"(?:^|\s)(?:이|그|저|요)\s*약(?!간|국|사)|이거|그거|저거|이것|그것|저것|이\s*제품|그\s*제품")
# AI가 증상 칸에 넣기도 하는 주의 대상 말. 증상이 아니에요 (주의 대상 사전은 '임신했'처럼 문장 모양이라 낱말 하나는 못 잡아요)
NOT_SYMPTOM_WORDS = {"임신", "임부", "임산부", "수유", "모유", "출산", "노인", "고령", "소아", "어린이", "아기", "유아"}
# 위 목록 밖의 증상을 약 이름 없이 말하면 (11/12 실제 대화: 타이레놀이 담긴 채 "계단 오르면 숨이 차요" → 타이레놀 복용법)
SYMPTOM_CARE_ANSWER = (
    "'{symptom}'은(는) 약보다 진료가 먼저일 수 있는 증상이에요. 증상이 계속되거나 심해지면 병원 진료를 받으세요. "
    "숨쉬기가 많이 힘들거나 가슴이 아프면 바로 119에 연락하세요."
)


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


# 인사만 한 말 (앞 대화·담긴 약과 상관없이 쓰는 법 안내). 문장 전체가 인사일 때만 ("안녕하세요 타이레놀 몇 번?"은 아님)
GREETING = re.compile(
    r"\s*(?:고마워요?|고맙습니다|감사(?:합니다|해요)?|안녕(?:하세요)?|반가워요?|반갑습니다|수고(?:하세요|하셨습니다)?|"
    r"ㄳ|ㄱㅅ|thanks?|thank\s*you|hi|hello)\s*[.!~^ㅎㅋ]*\s*",
    re.IGNORECASE,
)


# 질문 속 나이·사람: 65세 이상이면 노인. 새 나이·사람이 나오면 앞 대화의 주의 대상(임신·어린이 …)은 쓰지 않아요
# (11/12 시험: "지르텍 7살 아이" 다음 "우리 아버지가 80세인데 이 약 먹어도 돼?" → '어린이' 기준으로 답함)
AGE_IN_TEXT = re.compile(r"(?<!\d)(\d{1,3})\s*(?:세|살)")
ELDER_AGE = 65
NEW_SUBJECT = re.compile(r"아버지|어머니|아빠|엄마|할머니|할아버지|남편|아내|아들|딸|동생|친구|제가|저는|내가|나는")


# 설명서(e약은요·허가정보) 주의사항에서 대상별로 찾을 말 (11/12 팀원 제보: DUR 목록에 없는 약은 "찾지 못했어요"로 끝나
# 타이레놀의 '12세 미만', 지르텍의 '노인·임부 상의' 같은 설명서 내용을 빠뜨렸어요)
LABEL_WORDS = {
    "임부": r"임부|임신|임산부",
    "소아": r"소아|어린이|영아|유아|신생아|\d+\s*세\s*미만|\d+\s*개월\s*미만",
    "노인": r"고령|노인",
}
LABEL_STRONG = re.compile(r"복용하지\s*마|투여하지\s*말|사용하지\s*마|금기")
LABEL_SENTENCE_LIMIT = 3


def _label_sentences(drug: dict, target: str) -> list[str]:
    """주의사항(atpn_warn·atpn)에서 대상 말이 든 문장. 금지 문장이 먼저, 최대 3개
    설명서 문장은 대상을 10개씩 나열해서 길어요: 대상 부분 앞뒤와 문장 끝(상의하십시오/복용하지 마십시오)만 남겨요"""
    pattern = LABEL_WORDS[target]
    found = []
    for field in ("atpn_warn", "atpn"):
        # 번호 뒤의 점("(7. 임부 …")에서는 나누지 않아요 (허가정보는 번호 목록이 많아요)
        for sentence in re.split(r"(?<=[^\d][.。])\s+|\n+", str(drug.get(field) or "")):
            sentence = re.sub(r"\s+", " ", sentence).strip()
            match = re.search(pattern, sentence)
            if not match or len(sentence) < 15:   # "5) 고령자" 같은 머리말 조각은 빼요
                continue
            if len(sentence) > 150:
                start = max(0, match.start() - 50)
                end = match.end() + 50
                tail = len(sentence) - 40
                # 대상 부분과 문장 끝이 겹치면 이어서 보여 줘요 (같은 말이 두 번 나오지 않게)
                sentence = ("…" if start else "") + (sentence[start:] if end >= tail else sentence[start:end] + " … " + sentence[tail:])
            if sentence not in found:
                found.append(sentence)
    found.sort(key=lambda s: not LABEL_STRONG.search(s))
    return found[:LABEL_SENTENCE_LIMIT]


def _drug_cautions_answer(item_name: str, item_seq: str, targets: list[str], from_before: bool,
                          drug: dict | None = None) -> str | None:
    """약 하나의 식약처 DUR 임부·소아·노인 자료 + 설명서 주의사항으로 답을 써요 (AI 안 부름)
    DUR 조회에 실패하면 None (원래 흐름으로)"""
    name = base_name(item_name)
    label_source = "허가정보 주의사항" if (drug or {}).get("has_easy") is False else "설명서(e약은요)"
    lines = []
    if from_before:
        lines += [f"앞에서 말씀하신 '{', '.join(TARGET_NAMES[t] for t in targets)}'을(를) 기준으로, "
                  f"용량보다 먼저 {name}의 식약처 DUR 자료를 확인했어요.", ""]
    for target in targets:
        found = profile_cautions(target, [item_seq]).get(item_seq)
        if found is None:
            return None
        label = TARGET_NAMES[target]
        if found:
            for kind in dict.fromkeys(c["type"] for c in found):
                ingredients = ", ".join(dict.fromkeys(c["ingredient"] for c in found if c["type"] == kind and c.get("ingredient")))
                meaning = TYPE_MEANINGS.get(kind)
                lines.append(f"[{label}] {name}에는 {kind}{f'({meaning})' if meaning else ''} 자료가 있어요"
                             + (f": {ingredients}" if ingredients else "") + ".")
            lines += [f"- {c['content']}" for c in found if c.get("content")]
        else:
            lines.append(f"[{label}] {name}은(는) 식약처 DUR {label} 주의 목록에 있는 약은 아니에요.")
        # 설명서 문장은 DUR 목록에 없을 때만 (DUR이 있으면 그게 더 분명해요)
        sentences = [] if found else _label_sentences(drug or {}, target)
        if sentences:
            lines.append(f"다만 {label_source}에 이런 내용이 있어요:")
            lines += [f"- {s}" for s in sentences]
        elif not found:
            lines.append(f"{label_source}에서도 {label} 관련 내용을 찾지 못했어요. 자료에 없다고 안전하다는 뜻은 아니에요.")
        lines.append(CAUTION_MESSAGES[target])
    return "\n".join(lines)


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


def _find_drugs_in_parts(question: str, seqs: list[str]) -> tuple[list[dict], list[str], dict[str, list[dict]]]:
    """'A랑 B 같이 먹어도 돼요?'를 잇는 말로 나눠 조각마다 약을 찾아요 (조각마다 AI 한 번, 동시에).
    (찾은 약 목록, 같은 이름 제품이 여럿이라 정하지 못한 이름 목록, 그 이름마다 후보 제품)"""
    parts = [p.strip() for p in NAME_JOINERS.split(question) if len(p.strip()) >= 2][:3]
    if len(parts) < 2:
        return [], [], {}
    with ThreadPoolExecutor(max_workers=len(parts)) as pool:
        results = list(pool.map(_find_named_drug, parts))
    found, unclear, choices = [], [], {}
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
                choices[result["name"]] = result.get("candidates") or []
    return found, unclear, choices


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

def save_chat_log(question: str, result: dict, level: str, response_ms: int | None = None,
                  check: dict | None = None, meta: dict | None = None):
    """check: AI 답변 검증 기록 (chat_answer._answer_from_official_info가 채움). AI를 안 부른 답은 비어 있어요
    막힌 초안은 사용자에게 보내지 않고 여기에만 남겨요. 질문처럼 개인정보 모양은 가리고, 90일 뒤 함께 지워요(privacy.py)
    meta: is_test(평가·시험 요청, X-Medi-Test 헤더), question_type(약확인처럼 답을 만든 쪽이 정한 종류)"""
    check = check or {}
    meta = meta or {}
    blocked = level in ("block", "redirect") or result.get("risk") == "위험 상황"

    if blocked:
        question_type = "차단"
    elif meta.get("question_type"):
        question_type = meta["question_type"]   # 약확인: 어느 약인지 되물은 답 (ask_which_drug)
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
                (question, answer, question_type, target_item_seq, item_name, is_test, blocked, block_reason, response_ms,
                 check_result, check_reason, retry_reason, rejected_draft, retry_ms)
                VALUES
                (:question, :answer, :question_type, :item_seq, :item_name, :is_test, :blocked, :block_reason, :response_ms,
                 :check_result, :check_reason, :retry_reason, :rejected_draft, :retry_ms)
            """),
            {
                "question": mask_personal(question),   # 개인정보 모양은 가려서 저장 (I-7)
                "answer": result["answer"],
                "question_type": question_type,
                "item_seq": result.get("item_seq"),
                "item_name": result.get("item_name"),   # 관리자 질문 기록 표의 '약' 칸
                "is_test": bool(meta.get("is_test")),
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
def ask(
    data: AskRequest,
    user: dict | None = Depends(get_optional_user),
    x_medi_test: str | None = Header(default=None),   # 평가 스크립트·시험 요청이 "1"을 붙여요 → 관리자 기록에서 빼요
):
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
    # 질문 기록에만 쓰는 정보 (응답에는 안 넣어요)
    log_meta: dict = {"is_test": x_medi_test == "1"}

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
        save_chat_log(question, result, level, round((time.monotonic() - started) * 1000), answer_check, log_meta)
        return result

    def ask_which_drug(answer: str):
        """어느 약인지 되묻는 답. 질문 기록에 '약확인'으로 남겨요 (예전에는 '분류 못 함'으로 섞였어요)"""
        log_meta["question_type"] = "약확인"
        return reply(answer, risk=risk)

    def _by_ingredient_or_symptom(question: str, parsed: dict, profile: str | None):
        """성분 이름 → 그 성분이 든 제품 후보 버튼 / 증상 → 그 증상에 쓰는 약 목록. 둘 다 없으면 None
        약을 골라 주지는 않아요. 목록은 효능에 그 말이 적힌 약의 일부이고, 추천 거절(redirect)과 같은 안내를 달아요"""
        ingredient = (parsed.get("ingredient") or "").strip()
        if ingredient:
            try:
                _, items, _, _ = search_by_ingredient(ingredient, size=INGREDIENT_PICK_LIMIT)
            except httpx.HTTPError:
                items = []
            if items:
                extras["candidates"] = [_ref(c) for c in items]
                return ask_which_drug(f"{ingredient} 성분이 든 약이 여러 개예요. 어느 약인지 골라 주세요.")

        symptom = find_symptom(question) or (parsed.get("symptom") or "").strip()
        if not symptom or symptom not in common_symptoms() | LISTABLE_SYMPTOMS_EXTRA:
            return None
        log_meta["question_type"] = "증상"
        # 임부·소아·노인처럼 주의 대상이면 목록 없이 상담 안내만 (추천 거절과 같은 규칙)
        if caution_targets(question, profile):
            result = reply(
                f"'{symptom}'에 쓰는 약은 여러 가지인데, 주의가 필요한 분이라 약을 목록으로 보여 드리지 않아요. "
                "드시려는 약 이름을 알려 주시거나, 약사와 먼저 상담해 주세요.",
                source="안내", risk=risk,
            )
            result["items"], result["items_note"] = [], REDIRECT_SEARCH_NOTE
            return result
        try:
            _, items = search_by_efcy(symptom, size=REDIRECT_DRUG_LIMIT)
        except httpx.HTTPError:
            items = []
        result = reply(
            f"'{symptom}'에 쓰는 약을 찾아봤어요. 약 이름을 알려 주시면 그 약의 공식 정보로 답할게요. "
            "아래 약을 누르면 자세한 정보를 볼 수 있어요.",
            source=SOURCE, risk=risk,
        )
        result["items"] = [{"item_seq": i["item_seq"], "item_name": i["item_name"], "entp_name": i["entp_name"]} for i in items]
        result["items_note"] = REDIRECT_LIST_NOTE if items else REDIRECT_SEARCH_NOTE
        return result

    def emergency_reply(answer: str, source: str | None = None):
        result = {**make_reply(
            answer,
            source=source,
            risk="위험 상황",
        ), **extras}

        try:
            save_chat_log(question, result, "block", round((time.monotonic() - started) * 1000), meta=log_meta)
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
    # AI가 '임신 중인데 타이레놀 먹어도 돼?'를 위험 상황으로 보고 119를 안내했어요 (11/12, 같은 질문 두 번 모두)
    # 앞으로 먹어도 되는지 묻기만 하고 이미 먹은 이야기가 없으면 개인 복용 질문으로 봐요
    # 응급 표현·과다복용은 위의 안전 사전(check_safety)이 먼저 막아요
    if risk == "위험 상황" and ASK_BEFORE_TAKING.search(question) and not ALREADY_TAKEN.search(question):
        risk = analysis["risk"] = "개인 복용 질문"
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

    # ── 약 정하기 (11/12 구조 정리) ───────────────────────────────────────────
    # 이 질문이 어느 약 이야기인지 decide_drug 한 곳에서 정해요. 순서:
    #   ① 질문에 약 이름이 있으면 그 약 (코드가 찾음)
    #   ② 이름이 없으면 먼저 "담긴 약 이야기인가?"를 봐요. "이 약"·"이거" 같은 말이 없으면 담긴 약에 붙이지 않아요
    #      진료가 먼저인 증상 → 진료 안내 / 약 종류 + 임부·소아·노인 → DUR 자료 / 인사·약국 → 쓰는 법 안내
    #      담긴 약이 없으면: 성분 → 제품 버튼, 흔한 증상 → 약 목록
    #   ③ 그래도 모르면 AI 판단(keep·switch)을 마지막에 써요
    #   ④ 끝까지 못 정하면 "어느 약이에요?" (후보가 있으면 버튼과 함께)
    # 예전에는 네 방식(옛 drug_name·코드·AI keep/switch·AI 다시 검색)이 차례로 섞여, 담긴 약이 있으면
    # 임신·약국 질문까지 모두 그 약에 붙었어요 (11/12 실제 대화)
    def pick_reply(message: str, candidates: list[dict]):
        extras["candidates"] = [_ref(c) for c in candidates]
        result = ask_which_drug(message)
        result["total"] = len(candidates)   # 옛 화면용 목록 (계약 7장 5단계에서 지움)
        result["items"] = candidates
        return result

    def decide_drug():
        """(바로 보낼 답, None) 또는 (None, 답할 약의 품목번호)"""
        named_status = named.get("status")
        parsed = named.get("parsed") or {}
        drug_action = analysis["drug_action"]
        new_drug_name = analysis.get("new_drug_name")

        # 인사만 했으면 앞 대화·담긴 약과 상관없이 쓰는 법 안내 (11/12 실제 대화: 나이를 물은 뒤 "고마워요" → 또 나이를 물음)
        if GREETING.fullmatch(question):
            return reply(GUIDE_ANSWER, source="안내", risk=risk), None

        # ① 질문에 약 이름
        if named_status == "found" and (named.get("drug") or {}).get("item_seq"):
            target = str(named["drug"]["item_seq"])
            # 함께·비교 질문인데 지금 약도 질문에 적었으면 지금 약을 유지하고, 찾은 약은 담기만 해요 (#94)
            if (current_seq and target != current_seq and COMPARE_WORDS.search(question)
                    and _mentions(selected_item_name, question)):
                if target not in seqs:
                    extras["add_drugs"] = [_ref(named["drug"])]
                target = current_seq
            return None, target
        if named_status == "ambiguous":
            candidates = named.get("candidates") or []
            # 후보 중에 이 대화의 약이 있으면 그 약 (지금 약이 먼저): ● 타이레놀정500 + "타이레놀 하루 몇 번?"
            in_list = [c for c in candidates if str(c.get("item_seq")) in seqs]
            pick = next((c for c in in_list if str(c["item_seq"]) == current_seq), in_list[0] if in_list else None)
            if pick:
                return None, str(pick["item_seq"])
            return pick_reply(PICK_MESSAGE, candidates), None
        if named.get("name"):
            # 이름은 적었는데 못 찾음. 담긴 약도 없으면 바로 안내, 있으면 ③에서 AI 판단으로
            if not current_seq:
                return ask_which_drug(NOT_FOUND_MESSAGE), None
        else:
            # ② 약 이름이 없음
            symptom = find_symptom(question) or (parsed.get("symptom") or "").strip()
            # AI가 '임신'·'수유' 같은 주의 대상을 증상 칸에 넣기도 해요. 그건 증상이 아니라 아래 약 종류·개인 질문으로 (11/12)
            if symptom and (symptom in NOT_SYMPTOM_WORDS or caution_targets(symptom)):
                symptom = ""
            if symptom and symptom not in common_symptoms() | LISTABLE_SYMPTOMS_EXTRA:
                # "이 약 먹고 숨이 차요"처럼 담긴 약을 가리켜도 진료 안내가 먼저예요
                log_meta["question_type"] = "증상"
                return reply(SYMPTOM_CARE_ANSWER.format(symptom=symptom), source="안내", risk=risk), None
            if not (current_seq and DRUG_REFERENCE.search(question)):
                drug_type = find_drug_type(question)
                targets = [t for t in caution_targets(question, profile) if t in DUR_TARGETS] if drug_type else []
                if targets:
                    log_meta["question_type"] = "약확인"
                    return reply(
                        type_cautions_answer(type_cautions(drug_type, targets)),
                        source="식품의약품안전처 DUR", risk=risk,
                    ), None
                if category == "기타" and not new_drug_name:
                    return reply(GUIDE_ANSWER, source="안내", risk=risk), None
                if not current_seq and not (drug_action == "switch" and new_drug_name):
                    found = _by_ingredient_or_symptom(question, parsed, profile)
                    if found:
                        return found, None

        # ③ AI 판단: 지금 약 그대로(keep) 또는 AI가 찾은 다른 약 이름(switch)
        if drug_action == "keep" and current_seq:
            return None, current_seq
        if drug_action == "switch" and new_drug_name:
            try:
                search_result = find_chat_drug(new_drug_name)
            except httpx.HTTPError as exc:
                raise HTTPException(status_code=503, detail="약 정보 서버가 응답하지 않아요.") from exc
            status = search_result.get("status") if isinstance(search_result, dict) else None
            if status == "found" and (search_result.get("drug") or {}).get("item_seq"):
                return None, str(search_result["drug"]["item_seq"])
            if status == "ambiguous":
                return pick_reply(PICK_MESSAGE, search_result.get("candidates") or []), None
            return ask_which_drug(NOT_FOUND_MESSAGE), None

        # ④ 못 정함
        return ask_which_drug(WHICH_MESSAGE), None

    early, target_item_seq = decide_drug()
    if early is not None:
        return early

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
        unclear, choices = [], {}
        if NAME_JOINERS.search(question):
            found, unclear, choices = _find_drugs_in_parts(question, seqs)
            for ref in found:
                if ref["item_seq"] not in pool and len(pool) < MAX_TOGETHER:
                    pool[ref["item_seq"]] = ref["item_name"]
                    if ref["item_seq"] not in seqs:
                        extras["add_drugs"] = extras["add_drugs"] + [ref]
        # 짝이 안 되는데 질문에 적은 다른 약이 제품이 여럿이라 못 정했으면, "약을 하나 더 담아 주세요" 대신 그 약을 고르게 해요 (11/12)
        # 예: 타이레놀정500을 담고 "타이레놀이랑 판콜에이 같이 먹어도 돼?" → 판콜에이 제품 버튼 → 고르면 두 약으로 다시 물어 DUR 판정
        # 대화에 다른 약이 담겨 있어 짝이 채워져도 마찬가지예요 (11/12 실제 대화: 아스피린이 담긴 채 물어서
        # 경동아스피린+타이레놀만 판정하고 "성분 겹침 없음" → 정작 물은 판콜에이(아세트아미노펜 겹침)는 빠짐)
        pick_name = next((name for name in unclear if choices.get(name)), None)
        if pick_name:
            extras["candidates"] = [_ref(c) for c in choices[pick_name]]
            extras["switched"] = False
            return ask_which_drug(f"'{pick_name}'은(는) 같은 이름의 제품이 여러 개예요. 함께 먹을 약을 골라 주세요.")
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

    # 개인 복용 질문에 임부·소아·노인이 나오면 (지금 질문·앞 대화·프로필), 그 약의 식약처 DUR 자료로 답해요 (11/12)
    # 예전: "이 약 임신했는데 먹어도 돼?" → 나이를 되묻고 "확정하기 어려워요"만, 판콜에이의 임부 금기는 말하지 않았어요.
    #       앞 대화에 '임신'이 있으면 "이거 하루에 몇 번?"도 이유 없이 "판단하기 어려워요"였어요
    if risk == "개인 복용 질문":
        now_targets = caution_targets(question)
        ages = [int(age) for age in AGE_IN_TEXT.findall(question)]
        if any(age >= ELDER_AGE for age in ages):
            now_targets.append("노인")
        new_subject = bool(ages) or bool(NEW_SUBJECT.search(question))
        before_targets = [] if new_subject else caution_targets(" ".join(user_utterances[1:]))
        # 지금 질문에 대상이 있으면 그 대상만 답해요. 없을 때만 앞 대화, 그것도 없으면 프로필 (11/12 팀원 제보:
        # "어린이가 먹어도 돼?"에 [임신 중] 줄까지 나왔어요)
        now_dur = [t for t in dict.fromkeys(now_targets) if t in DUR_TARGETS]
        before_dur = [t for t in dict.fromkeys(before_targets) if t in DUR_TARGETS]
        targets = now_dur or before_dur or ([profile] if profile in DUR_TARGETS else [])
        if targets:
            answer = _drug_cautions_answer(item_name, item_seq, targets, from_before=not now_dur, drug=drug)
            if answer:
                # 안전 검사가 끝에 같은 상담 문장을 붙이면 (질문에 '임신' 등이 있을 때) 여기서는 빼요
                warned = (safety.get("message") or "") if level == "warn" else ""
                answer = "\n".join(line for line in answer.split("\n") if not (line and line in warned))
                return reply(answer, item_seq, item_name, "식품의약품안전처 DUR", risk, category)

    # 임신·수유라고 했으면 나이를 되묻지 않아요 (성인이에요)
    pregnant_or_nursing = bool({"임부", "수유"} & set(caution_targets(" ".join(user_utterances))))
    if risk == "개인 복용 질문" and analysis["action"] == "clarify" and not (
        analysis["missing"] == "age" and pregnant_or_nursing
    ):
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
