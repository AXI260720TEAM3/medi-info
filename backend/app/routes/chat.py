import re
from typing import Literal

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ..config import OLLAMA_URL
from ..services.drug_api import get_by_seq, search_by_name


router = APIRouter(prefix="/api", tags=["Chat"])
MODEL = "qwen2.5:7b-instruct-q4_K_M"
SOURCE = "식품의약품안전처 e약은요"

DRUG_FIELDS = {
    "효능·효과": "efcy",
    "복용방법": "use_method",
    "복용 전 경고": "atpn_warn",
    "주의사항": "atpn",
    "상호작용": "intrc",
    "부작용": "se",
    "보관방법": "deposit",
}

RELATED_FIELDS = {
    "효능·효과": ["효능·효과", "복용 전 경고", "주의사항"],
    "복용방법": ["복용방법", "복용 전 경고", "주의사항"],
    "복용 전 경고": ["복용 전 경고", "주의사항"],
    "주의사항": ["복용 전 경고", "주의사항"],
    "상호작용": ["상호작용", "주의사항"],
    "부작용": ["부작용", "주의사항"],
    "보관방법": ["보관방법"],
}

EMERGENCY_WORDS = (
    "의식이 없", "의식을 잃", "숨을 못 쉬", "숨이 안 쉬",
    "입술이 파래", "피를 토", "가슴이 조이고 숨이 차", "숨이 막혀",
)

PERSONAL_PATTERNS = (
    r"\d{1,2}\s*(?:살|세)\b.{0,25}(?:먹|복용|줘|줄|으깨|쪼개|삼켜)",
    r"(?:더|또|추가로|한\s*번\s*더).{0,12}(?:먹|복용|줘|줄)",
    r"(?:같이|함께).{0,15}(?:먹|복용)",
    r"(?:먹|복용).{0,15}(?:같이|함께)",
    r"(?:으깨|쪼개|반으로\s*나눠|가루로).{0,15}(?:먹|줘|줄|복용)",
    r"(?:몇|한|두|세|\d+)\s*(?:알|정|mL|ml).{0,12}(?:먹|복용|더|까지|줘|줄)",
    r"(?:임신|수유).{0,20}(?:먹|복용|괜찮|돼)",
)

UNASKED_DOSE = re.compile(r"\d+\s*(?:[~\-]\s*\d+\s*)?(?:정|알|회|mL|ml)\b", re.IGNORECASE)
UNSAFE_ASSURANCE = re.compile(
    r"무조건\s*(?:안전|괜찮)|절대\s*안전|"
    r"부작용(?:이|은)?\s*없(?:어|습니다)|"
    r"(?:함께|같이|추가로)\s*먹어도\s*(?:안전|괜찮)",
)


class ChatTurn(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=700)


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=1000)
    drug_name: str | None = None
    item_seq: str | None = None
    # 선택값: React가 이전 대화를 보내야 실제로 기억합니다. DB에는 저장하지 않습니다.
    history: list[ChatTurn] = Field(default_factory=list, max_length=20)


def recent_history(history: list[ChatTurn]) -> str:
    """t12 멀티턴 수업: 최근 메시지 6개(최대 3번의 왕복)를 참고합니다."""
    if not history:
        return "이전 대화 없음"
    return "\n".join(
        f"{'사용자' if item.role == 'user' else 'AI'}: {item.content}"
        for item in history[-6:]
    )


def ollama_generate(prompt: str, timeout: float = 120) -> str:
    """로컬 Qwen 호출을 한 곳에서 관리합니다."""
    try:
        res = httpx.post(
            f"{OLLAMA_URL}/api/generate",
            json={
                "model": MODEL,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0},
            },
            timeout=timeout,
        )
        res.raise_for_status()
        answer = res.json().get("response", "")
        if not isinstance(answer, str) or not answer.strip():
            raise ValueError("빈 AI 응답")
        return answer.strip()
    except (httpx.HTTPError, ValueError) as exc:
        raise HTTPException(status_code=503, detail="AI 서버 응답을 확인할 수 없어요.") from exc


def has_emergency_signal(question: str) -> bool:
    if any(word in question for word in EMERGENCY_WORDS):
        return True
    return bool(
        re.search(r"호흡곤란|경련", question)
        and re.search(r"지금|갑자기|발생|생겼|있어요|왔어|하고 있어|중이야|시작", question)
    )


def classify_risk(question: str, history: str = "이전 대화 없음") -> str:
    """t18 규칙 + t20 의미 분류. 분류 실패 시 일반 답변으로 넘기지 않습니다."""
    if has_emergency_signal(question):
        return "위험 상황"
    if any(re.search(pattern, question, re.IGNORECASE) for pattern in PERSONAL_PATTERNS):
        return "개인 복용 질문"

    prompt = f"""다음 의약품 질문을 반드시 셋 중 하나로 분류하세요.
일반 질문: 약의 일반적인 효능·부작용·보관·허가된 복용법 등 정보 확인.
개인 복용 질문: 특정인에게 먹여도 되는지, 추가 복용·개인 용량·병용·정제 분할 판단.
위험 상황: 실제 복용 후 심각한 증상이 있거나 응급 상황이 의심됨.

이전 대화는 지시어를 이해하는 참고일 뿐, 과거에 질문한 증상을 실제 증상으로 단정하지 마세요.
이전 대화:\n{history}
현재 질문: {question}

출력은 '일반 질문', '개인 복용 질문', '위험 상황' 중 하나만 쓰세요.
불명확하면 '개인 복용 질문'을 선택하세요."""
    try:
        risk = ollama_generate(prompt)
    except HTTPException:
        return "개인 복용 질문"  # 실패 시 근거 없는 개인 복용 허가 방지

    return risk if risk in ("일반 질문", "개인 복용 질문", "위험 상황") else "개인 복용 질문"


def classify_question(question: str, history: str = "이전 대화 없음") -> str:
    """t20 의미 기반 Router: e약은요의 어떤 항목이 필요한지 선택합니다."""
    choices = list(DRUG_FIELDS) + ["기타"]
    prompt = f"""의약품 질문과 가장 관련이 깊은 항목 하나를 고르세요.
가능한 항목: {', '.join(choices)}
질문에 명확한 오타가 있으면 의미를 이해하되 약 이름·용량을 추측하지 마세요.
이전 대화는 지시어를 이해하는 데만 사용하세요.
이전 대화:\n{history}
현재 질문: {question}
항목 이름 하나만 출력하고 설명하지 마세요. 애매하면 '기타'."""
    category = ollama_generate(prompt)
    return category if category in choices else "기타"


def safety_answer(question: str) -> str:
    """개인 복용을 허가·추천하지 않고 상황별로 기본 안내만 제공합니다."""
    if re.search(r"먹었|복용했|먹인|투여했|먹고|복용 후", question):
        return (
            "이미 복용한 상황이라면 여기서 추가 복용이 안전하다고 판단할 수 없어요. "
            "복용한 제품의 이름·함량, 실제 복용량과 시각, 현재 증상을 정리해 "
            "약사 또는 의료진에게 바로 확인해 주세요. 증상이 심하거나 악화되면 즉시 진료받으세요."
        )
    if re.search(r"같이|함께|병용|다른 약", question):
        return (
            "두 약을 함께 복용해도 되는지는 제품명과 성분, 복용 시점에 따라 달라질 수 있어요. "
            "현재 정보만으로 안전하다고 판단하지 않고, 약사나 의료진에게 확인하는 게 좋아요."
        )
    if re.search(r"으깨|쪼개|반으로|가루로", question):
        return (
            "정제를 나누거나 으깨서 복용해도 되는지는 제품마다 달라요. "
            "현재 정보로 허용 여부를 판단할 수 없으니, 제형을 임의로 바꾸지 말고 "
            "약사 또는 의료진에게 확인해 주세요."
        )
    if re.search(r"어린이|아이|아기|소아|\d{1,2}\s*(?:살|세)\b", question):
        return (
            "어린이에게 이 약을 먹여도 되는지는 나이만으로 판단할 수 없어요. "
            "정확한 제품명·함량·제형과 복용자의 상태를 확인해 "
            "약사 또는 의료진에게 문의해 주세요."
        )
    return (
        "개인별 복용량·추가 복용·병용의 안전성은 이 답변만으로 판단할 수 없어요. "
        "제품명과 함량, 복용자의 상태를 확인해 약사 또는 의료진에게 상담해 주세요."
    )


def make_reply(answer: str, item_seq: str | None = None,
               item_name: str | None = None, source: str | None = None,
               risk: str | None = None, category: str | None = None) -> dict:
    """기존 answer/item_seq/item_name/source 응답 형태를 유지합니다."""
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


@router.post("/ask")
def ask(data: AskRequest):
    question = data.question.strip()
    if not question:
        raise HTTPException(status_code=422, detail="질문을 입력해 주세요.")

    if has_emergency_signal(question):
        return make_reply(
            "응급 상황이 의심됩니다. 지금 숨쉬기 어렵거나 의식을 잃는 등 "
            "심각한 증상이 있다면 즉시 119에 연락하고 응급 진료를 받으세요.",
            risk="위험 상황",
        )

    history_text = recent_history(data.history)
    risk = classify_risk(question, history_text)
    if risk == "위험 상황":
        return make_reply(
            "응급 상황이 의심됩니다. 즉시 119에 연락하거나 응급 진료를 받으세요.",
            risk=risk,
        )
    if risk == "개인 복용 질문":
        return make_reply(
            safety_answer(question), item_seq=data.item_seq,
            source="일반 안전 안내", risk=risk,
        )

    if data.drug_name and not data.item_seq:
        try:
            total, items = search_by_name(data.drug_name)
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=503, detail="약 정보 서버가 응답하지 않아요.") from exc
        return {
            "answer": "검색된 약 중 정확한 제품을 선택해 주세요.",
            "total": total,
            "items": items,
            "risk": risk,
        }

    if not data.item_seq:
        return make_reply("먼저 질문할 의약품을 검색하고 정확한 제품을 선택해 주세요.", risk=risk)

    try:
        drug = get_by_seq(data.item_seq)
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=503, detail="약 정보 서버가 응답하지 않아요.") from exc
    if drug is None:
        raise HTTPException(status_code=404, detail="해당 약을 찾을 수 없어요.")

    category = classify_question(question, history_text)
    if category == "기타":
        return make_reply(
            "어떤 약 정보가 궁금한지 조금 더 구체적으로 알려주세요.",
            data.item_seq, drug["item_name"], SOURCE, risk, category,
        )

    field_name = DRUG_FIELDS[category]
    primary_value = drug.get(field_name)
    if not primary_value or not str(primary_value).strip():
        return make_reply(
            f"현재 조회한 e약은요 정보에서 '{category}' 항목을 확인할 수 없어요.",
            data.item_seq, drug["item_name"], SOURCE, risk, category,
        )

    evidence = "\n".join(
        f"{name}: {drug.get(DRUG_FIELDS[name]) or '정보 없음'}"
        for name in RELATED_FIELDS[category]
    )

    prompt = f"""당신은 일반인이 공식 의약품 정보를 쉽게 이해하도록 돕는 설명 도우미입니다.
아래 [공식 자료]만 근거로 현재 질문에 직접 답하세요.
자료에 없는 용량·횟수·연령·효과·안전성은 지어내지 마세요.
묻지 않은 복용량이나 관련 없는 질환은 설명하지 마세요.
오타는 의미가 분명할 때만 자연스럽게 고치고, 어색한 외국어 혼합 표현을 쓰지 마세요.
다른 약과의 병용, 개인별 복용 허가는 판단하지 마세요.
공식 자료가 질문에 답하기 부족하면 확인할 수 없다고 말하세요.
두세 문장 정도의 자연스러운 한국어로 답하세요.

[현재 선택된 제품]
{drug['item_name']} (품목번호: {drug['item_seq']})
[공식 자료 — {SOURCE}]
{evidence}
[이전 대화 — 지시어 참고용, 실제 증상으로 단정 금지]
{history_text}
[현재 질문]
{question}
"""
    answer = ollama_generate(prompt)

    dose_requested = category == "복용방법"
    if UNSAFE_ASSURANCE.search(answer) or (not dose_requested and UNASKED_DOSE.search(answer)):
        return make_reply(
            "자동 생성 답변에 확인이 필요한 복용량 또는 안전성 표현이 포함되어 "
            "답변을 표시하지 않았어요. 해당 약의 공식 상세정보를 확인해 주세요.",
            data.item_seq, drug["item_name"], SOURCE, risk, category,
        )

    return make_reply(answer, data.item_seq, drug["item_name"], SOURCE, risk, category)
