# 위험 증상: "+"로 나눈 조각이 질문에 모두 들어 있으면 AI를 부르지 않고 119를 안내한다
DANGER_KEYWORDS = ["가슴+아파", "가슴+통증", "가슴+조여", "숨+안", "의식+없", "경련"]


def _matches(keyword: str, text: str) -> bool:
    return all(part in text for part in keyword.split("+"))


def check_safety(question: str) -> dict:
    text = question.replace(" ", "")

    for keyword in DANGER_KEYWORDS:
        if _matches(keyword, text):
            return {
                "level": "block",
                "matched": [keyword],
                "message": "응급 상황일 수 있습니다. 지금 바로 119에 전화하세요.",
            }

    return {"level": "pass", "matched": [], "message": None}
