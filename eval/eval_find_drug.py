import csv
import sys

from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, "backend")

from app.services.search import find_drug

PATH = sys.argv[1] if len(sys.argv) > 1 else "data/eval/find_drug_questions.csv"

def is_correct(row, result):
    if result["status"] != row["expected_status"]:
        return False
    if result["status"] == "found":
        return result["drug"]["item_name"].startswith(row["expected_name"])
    if result["status"] == "ambiguous":
        return any(row["expected_name"] in d["item_name"] for d in result["candidates"])
    return True

with open(PATH, encoding="utf-8-sig") as f:
    rows = list(csv.DictReader(f))

hit = 0
for row in rows:
    result = find_drug(row["question"])
    ok = is_correct(row, result)
    hit += ok

    if result["status"] == "found":
        got = result["drug"]["item_name"]
    elif result["status"] == "ambiguous":
        got = f"후보 {len(result['candidates'])}개"
    else:
        got = "-"
    print("O" if ok else "X", row["question"], "|", result["status"], got,
          "| 정답:", row["expected_status"], row["expected_name"])
print(f"\n맞힌 수: {hit}/{len(rows)}")