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
    for row in _load_words():
        pos = joined.find(row["word"])
        if pos != -1:
            hits.append((pos, row["standard"]))
    
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