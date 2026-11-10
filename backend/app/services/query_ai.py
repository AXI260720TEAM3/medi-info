import json
import httpx
from ..config import OLLAMA_URL

MODEL = "qwen2.5:7b-instruct-q4_K_M"

# AI가 꼭 이 모양으로만 답하게 하는 양식 (JSON Schema)
SCHEMA = {
    "type": "object",
    "properties": {
        "drug_name": {"type": ["string", "null"]},
        "ingredient": {"type": ["string", "null"]},
        "company": {"type": ["string", "null"]},
        "symptom": {"type": ["string", "null"]},
    },
    "required": ["drug_name", "ingredient", "company", "symptom"],
}

SYSTEM = (
    "너는 약국 접수 직원이야. 손님 말에서 네 가지를 뽑아 JSON으로만 답해.\n"
    "- drug_name: 손님이 직접 말한 약(제품) 이름. 처음 보는 이름이거나 철자가 틀려도 약 이름으로 보이면 "
    "손님이 쓴 글자 그대로 적어. 말하지 않았으면 null. 절대 지어내지 마.\n"
    "- ingredient: 손님이 '성분'으로 찾는다고 말한 것 (예: 아세트아미노펜, 이부프로펜, 로라타딘). "
    "'~ 들어간 약', '~ 성분' 처럼 성분으로 찾을 때만. "
    "'○○ 효능', '○○ 부작용'처럼 이름 하나만 말하면 성분이 아니라 drug_name이야. 없으면 null.\n"
    "- company: 손님이 말한 제약회사 이름 (예: 동아제약, 한국얀센, 종근당). '~ 회사 약', '~에서 만든 약'일 때. 없으면 null.\n"
    "- symptom: 손님이 직접 말한 증상을 의약품 설명서에 쓰는 공식 낱말 하나로 바꾼 것. 반드시 한글로만 써. "
    "손님이 증상을 말하지 않았으면 null. 약 이름만 보고 증상을 짐작하지 마.\n"
    "예) 머리가 지끈거려요 → 두통 / 열이 나요 → 발열 / 속이 쓰려요 → 속쓰림 / "
    "배가 아프고 화장실을 자주 가요 → 설사 / 며칠째 화장실을 못 가요 → 변비\n"
    "예) 펜잘 부작용 → drug_name=펜잘 / 우루사 먹는 법 → drug_name=우루사 / 지르텍 효능 → drug_name=지르텍 / "
    "아세트아미노펜 들어간 약 → ingredient=아세트아미노펜 / 종근당 약 → company=종근당"
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