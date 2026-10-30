import json
import httpx
from ..config import OLLAMA_URL

MODEL = "qwen2.5:7b-instruct-q4_K_M"

# AI가 꼭 이 모양으로만 답하게 하는 양식 (JSON Schema)
SCHEMA = {
    "type": "object",
    "properties": {
        "drug_name": {"type": ["string", "null"]},
        "symptom": {"type": ["string", "null"]},
    },
    "required": ["drug_name", "symptom"],
}

SYSTEM = (
    "너는 약국 접수 직원이야. 손님 말에서 두 가지를 뽑아 JSON으로만 답해.\n"
    "- drug_name: 손님이 직접 말한 약 이름. 말하지 않았으면 null. 절대 지어내지 마.\n"
    "- symptom: 손님이 직접 말한 증상을 의약품 설명서에 쓰는 공식 낱말 하나로 바꾼 것. 반드시 한글로만 써. "
    "손님이 증상을 말하지 않았으면 null. 약 이름만 보고 증상을 짐작하지 마.\n"
    "예) 머리가 지끈거려요 → 두통 / 열이 나요 → 발열 / 속이 쓰려요 → 속쓰림 / "
    "배가 아프고 화장실을 자주 가요 → 설사 / 며칠째 화장실을 못 가요 → 변비"
)

def parse_query(text):
    res = httpx.post(
        f"{OLLAMA_URL}/api/chat",
        json={
            "model": MODEL,
            "stream": False,
            "format": SCHEMA,
            "options": {"temperature": 0},
            "messages": [
                {"role":"system", "content": SYSTEM},
                {"role": "user", "content": text},
            ],
        },
        timeout=60,
    )
    res.raise_for_status()
    return json.loads(res.json()["message"]["content"])