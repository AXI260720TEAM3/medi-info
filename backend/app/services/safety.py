from sqlalchemy import text

from ..database import SessionLocal

# action마다 손님에게 보여 줄 안내
ACTION_MESSAGES = {
    "119": "응급 상황일 수 있습니다. 지금 바로 119에 전화하세요.",
    "109": "혼자 견디기 힘드시면 자살예방 상담전화 109에 전화하세요. 24시간 상담할 수 있습니다.",
    "응급실": "가까운 응급실로 바로 가세요.",
    "병원": "약보다 병원 진료가 먼저 필요합니다. 병원에 가 보세요.",
}

# 약을 골라 달라는 표현 (띄어쓰기를 지운 질문과 비교)
RECOMMEND_KEYWORDS = [
    "약추천", "약좀추천", "제추천", "연고추천",
    "무슨약을", "무슨약먹", "어떤약을", "어떤약이+좋", "어떤게좋",
    "에뭐먹으면", "에뭐먹어야", "약뭐먹", "뭐가좋아",
    "잘듣는약", "골라줘",
]
RECOMMEND_MESSAGE = "특정 약을 골라 드릴 수는 없습니다. 증상에 쓰는 약의 정보를 보여 드릴 수 있으니, 어떤 약이 맞는지는 약사와 상담해 보세요."

# 주의 대상마다 손님에게 보여 줄 안내
CAUTION_MESSAGES = {
    "임부": "임신 중이라면 약을 드시기 전에 의사나 약사와 먼저 상담하세요.",
    "수유": "수유 중이라면 약 성분이 모유로 나올 수 있으니 약사와 먼저 상담하세요.",
    "소아": "어린이는 나이와 몸무게에 따라 먹는 양이 다르니 약사와 먼저 상담하세요.",
    "노인": "어르신은 약의 영향을 더 크게 받을 수 있으니 약사와 먼저 상담하세요.",
    "복용중": "지금 드시는 약이 있다면 함께 먹어도 되는지 약사와 먼저 확인하세요.",
}


def _load_danger_keywords():
    with SessionLocal() as db:
        return db.execute(
            text("SELECT keyword, action FROM symptom_keyword WHERE is_active")
        ).mappings().all()


def _matches(keyword: str, text: str) -> bool:
    return all(part in text for part in keyword.split("+"))


def _load_caution_keywords():
    with SessionLocal() as db:
        return db.execute(
            text("SELECT keyword, target FROM caution_keyword")
        ).mappings().all()


def _check_cautions(text: str):
    matched = []
    messages = []
    for row in _load_caution_keywords():
        if _matches(row["keyword"], text):
            matched.append(row["keyword"])
            message = CAUTION_MESSAGES[row["target"]]
            if message not in messages:
                messages.append(message)
    return matched, " ".join(messages)


def check_safety(question: str) -> dict:
    text = question.replace(" ", "")

    for row in _load_danger_keywords():
        if _matches(row["keyword"], text):
            return {
                "level": "block",
                "matched": [row["keyword"]],
                "message": ACTION_MESSAGES[row["action"]],
            }

    caution_matched, caution_message = _check_cautions(text)

    for keyword in RECOMMEND_KEYWORDS:
        if _matches(keyword, text):
            return {
                "level": "redirect",
                "matched": [keyword] + caution_matched,
                "message": f"{RECOMMEND_MESSAGE} {caution_message}".strip(),
            }

    if caution_matched:
        return {
            "level": "warn",
            "matched": caution_matched,
            "message": caution_message,
        }

    return {"level": "pass", "matched": [], "message": None}
