# ============================================================
# 파일명: chat_common.py
# 역할: AI 채팅에서 공통으로 사용하는 설정 및 AI 호출
#
# 주요 기능
# - 의약품 정보 항목 및 관련 항목 설정
# - 질문 위험도 및 추가 질문 설정
# - ollama_generate(): Ollama AI 모델 호출
#
# 연관 파일: routes/chat.py, chat_analysis.py, chat_answer.py
# ============================================================

import httpx
from fastapi import HTTPException

from ..config import OLLAMA_URL


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
    "효능·효과": ["효능·효과", "복용 전 경고"],
    "복용방법": ["복용방법", "복용 전 경고", "주의사항"],
    "복용 전 경고": ["복용 전 경고", "주의사항"],
    "주의사항": ["복용 전 경고", "주의사항"],
    "상호작용": ["상호작용", "주의사항"],
    "부작용": ["부작용", "주의사항"],
    "보관방법": ["보관방법"],
}

RISKS = ("일반 질문", "개인 복용 질문", "위험 상황")

FOLLOWUPS = {
    "age": "복용할 사람은 몇 살인가요?",
    "purpose": "어떤 증상이나 목적으로 복용하려는 건가요?",
    "other": "복용하려는 상황을 조금 더 자세히 알려주시겠어요?",
}


def ollama_generate(
    prompt: str,
    timeout: float = 120,
    json_mode: bool = False,
) -> str:
    payload = {
        "model": MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0},
    }

    if json_mode:
        payload["format"] = "json"

    try:
        res = httpx.post(
            f"{OLLAMA_URL}/api/generate",
            json=payload,
            timeout=timeout,
        )
        res.raise_for_status()
        answer = res.json().get("response", "")

        if not isinstance(answer, str) or not answer.strip():
            raise ValueError("빈 AI 응답")

        return answer.strip()

    except (httpx.HTTPError, ValueError) as exc:
        raise HTTPException(
            status_code=503,
            detail="AI 서버 응답을 확인할 수 없어요.",
        ) from exc