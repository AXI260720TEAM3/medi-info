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


def _load_danger_keywords():
    with SessionLocal() as db:
        return db.execute(
            text("SELECT keyword, action FROM symptom_keyword WHERE is_active")
        ).mappings().all()


def _matches(keyword: str, text: str) -> bool:
    return all(part in text for part in keyword.split("+"))


def check_safety(question: str) -> dict:
    text = question.replace(" ", "")

    for row in _load_danger_keywords():
        if _matches(row["keyword"], text):
            return {
                "level": "block",
                "matched": [row["keyword"]],
                "message": ACTION_MESSAGES[row["action"]],
            }

    for keyword in RECOMMEND_KEYWORDS:
        if _matches(keyword, text):
            return {
                "level": "redirect",
                "matched": [keyword],
                "message": RECOMMEND_MESSAGE,
            }

    return {"level": "pass", "matched": [], "message": None}
