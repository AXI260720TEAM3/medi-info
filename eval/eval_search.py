import csv
import sys

from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, "backend")

from app.services.query_ai import parse_query
from app.services.synonym import find_symptom

with open("data/eval/search_questions.csv", encoding="utf-8-sig") as f:
    rows = list(csv.DictReader(f))

before_hit = 0
after_hit = 0

for row in rows:
    before = parse_query(row["question"])["symptom"]
    after = find_symptom(row["question"]) or before

    if before == row["expected"]:
        before_hit += 1
    if after == row["expected"]:
        after_hit += 1

    mark = "O" if after == row["expected"] else "X"
    print(mark, row["question"], "|", before, "→", after, "| 정답:", row["expected"])

print(f"\nAI만:      {before_hit}/{len(rows)}")
print(f"AI + 사전: {after_hit}/{len(rows)}")