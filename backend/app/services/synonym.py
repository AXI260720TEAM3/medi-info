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