import re

from sqlalchemy import text

from ..database import SessionLocal

# 약을 많이 먹었다는 표현 (띄어쓰기를 지운 질문과 비교). 개월은 나이라서 뺀다
OVERDOSE_PATTERN = re.compile(
    r"(\d+|다섯|여섯|일곱|여덟|아홉|열|스무|스물|서른|마흔|쉰|백)(알|정|캡슐|개(?!월)|포|병|봉)"
    r"[을를이나씩도]{0,3}(?:한꺼번에|한번에|다)?(?:먹었|먹어버|먹은것|삼켰|복용했)"
)
OVERDOSE_MIN = 5
PILL_UNITS = ("알", "정", "캡슐")  # 이 단위는 약이 분명하고, 개·병 같은 단위는 약 단어가 있을 때만 본다
DRUG_WORDS = ("약", "진통제", "해열제", "소화제", "수면제", "영양제", "지사제", "항생제")

# 생후 3개월 미만 아기의 열은 바로 응급실로 가야 한다. 나이는 숫자라서 단어 사전 대신 여기서 본다
INFANT_AGE_PATTERN = re.compile(r"(\d+|한|두|세)(주|달|개월)")
KOREAN_COUNTS = {"한": 1, "두": 2, "세": 3}
BABY_WORDS = ("아기", "애기", "신생아", "생후")
FEVER_WORDS = ("열이", "열나", "열났", "발열", "고열", "미열")

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
    "잘듣는약", "골라줘", "좋은약+알려", "좋은약+있",
]
# 약 이름을 몰라도 추천 요청으로 보는 넓은 표현. 약이 아닌 것을 추천해 달라는 질문은 뺀다
RECOMMEND_BROAD_KEYWORDS = ["추천좀", "추천해주세요", "추천해줘"]
NOT_DRUG_WORDS = ["약국", "병원", "음식"]
RECOMMEND_MESSAGE = "특정 약을 골라 드릴 수는 없습니다. 증상에 쓰는 약의 정보를 보여 드릴 수 있으니, 어떤 약이 맞는지는 약사와 상담해 보세요."

# 주의 대상마다 손님에게 보여 줄 안내
CAUTION_MESSAGES = {
    "임부": "임신 중이라면 약을 드시기 전에 의사나 약사와 먼저 상담하세요.",
    "수유": "수유 중이라면 약 성분이 모유로 나올 수 있으니 약사와 먼저 상담하세요.",
    "소아": "어린이는 나이와 몸무게에 따라 먹는 양이 다르니 약사와 먼저 상담하세요.",
    "노인": "어르신은 약의 영향을 더 크게 받을 수 있으니 약사와 먼저 상담하세요.",
    "복용중": "지금 드시는 약이 있다면 함께 먹어도 되는지 약사와 먼저 확인하세요.",
}
# AI 답변에 나오면 안 되는 표현 (띄어쓰기를 지운 답변과 비교)
BANNED_PHRASES = [
    "약을드세요", "드시면됩니다", "추천합니다", "가장좋습니다",  # 약 골라 주기
    "인것같습니다", "로보입니다",                              # 진단
    "부작용이없", "먹어도괜찮", "안전합니다",                   # 안전 단정
    "완치", "확실히낫",                                       # 효과 단정
    "갈필요없",                                               # 진료 말리기
]


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


def _is_overdose(text: str) -> bool:
    for match in OVERDOSE_PATTERN.finditer(text):
        count, unit = match.groups()
        if count.isdigit() and int(count) < OVERDOSE_MIN:
            continue
        if unit in PILL_UNITS or any(word in text for word in DRUG_WORDS):
            return True
    return False


def _is_infant_fever(text: str) -> bool:
    """'생후 두 달 된 아기가 열이 39도' 처럼 3개월 미만 아기의 열인지 본다."""
    if not any(word in text for word in BABY_WORDS) or not any(word in text for word in FEVER_WORDS):
        return False
    for match in INFANT_AGE_PATTERN.finditer(text):
        count, unit = match.groups()
        count = int(count) if count.isdigit() else KOREAN_COUNTS[count]
        if (unit == "주" and count < 13) or (unit in ("달", "개월") and count < 3):
            return True
    return False


def check_safety(question: str) -> dict:
    text = question.replace(" ", "")

    for row in _load_danger_keywords():
        if _matches(row["keyword"], text):
            return {
                "level": "block",
                "matched": [row["keyword"]],
                "message": ACTION_MESSAGES[row["action"]],
            }

    if _is_overdose(text):
        return {
            "level": "block",
            "matched": ["과다복용 숫자"],
            "message": ACTION_MESSAGES["119"],
        }

    if _is_infant_fever(text):
        return {
            "level": "block",
            "matched": ["3개월 미만 아기 열"],
            "message": ACTION_MESSAGES["응급실"],
        }

    caution_matched, caution_message = _check_cautions(text)

    keywords = list(RECOMMEND_KEYWORDS)
    if not any(word in text for word in NOT_DRUG_WORDS):
        keywords += RECOMMEND_BROAD_KEYWORDS

    for keyword in keywords:
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


def find_banned(answer: str) -> list:
    text = answer.replace(" ", "")
    found = []
    for phrase in BANNED_PHRASES:
        if _matches(phrase, text):
            found.append(phrase)
    return found


def get_notice(code: str) -> str:
    with SessionLocal() as db:
        return db.execute(
            text("SELECT text FROM notice_text WHERE code = :code"),
            {"code": code},
        ).scalar_one()


def add_disclaimer(answer: str) -> str:
    return f"{answer}\n\n{get_notice('DISCLAIMER')}"
