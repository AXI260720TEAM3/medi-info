from sqlalchemy import text
from ..database import SessionLocal


def _load_words():
    with SessionLocal() as db:
        return db.execute(
            text("SELECT word, standard FROM synonym WHERE syn_type = '일상_공식'")
        ).mappings().all()

def find_symptom(question: str):
    joined = question.replace(" ","")

    hits = []
    rows = _load_words()
    for row in rows:
        pos = joined.find(row["word"])
        if pos != -1:
            hits.append((pos, row["standard"]))
    # 공식 증상 이름을 그대로 쓴 질문도 찾아요 (11/13: "두통이 있어요"·"두통"은 사전의 일상어 '머리가 아프'에 없어서
    # AI에게 넘어갔고, AI가 '두통'을 약 이름으로 읽으면 "의약품을 찾지 못했어요"로 끝났어요)
    for standard in {row["standard"] for row in rows}:
        pos = joined.find(standard.replace(" ", ""))
        if pos != -1:
            hits.append((pos, standard))

    if not hits:
        return None
    return min(hits)[1]

def common_symptoms() -> set[str]:
    """증상 사전(일상어 → 공식)에 있는 공식 증상들. 일반의약품으로 흔히 다루는 증상이에요 (두통·인후통·콧물 …)"""
    return {row["standard"] for row in _load_words()}

def fix_drug_typo(name: str):
    with SessionLocal() as db:
        rows = db.execute(
            text("SELECT word, standard FROM synonym WHERE syn_type = '오타_제품명'")
        ).mappings().all()

    for row in rows:
        name = name.replace(row["word"], row["standard"])
    return name