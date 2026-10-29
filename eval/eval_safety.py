import csv
import sys

from dotenv import load_dotenv

load_dotenv()                 # ① .env → 환경변수
sys.path.insert(0, "backend") # ② backend 폴더에서 app을 찾게

from app.services.safety import check_safety  # ③ 이제 불러와도 안전

with open("data/eval/safety_questions.csv", encoding="utf-8-sig") as f:
    rows = list(csv.DictReader(f))

block_total = 0   # 막아야 할 질문 수
block_hit = 0     # 그중 실제로 막은 수
pass_total = 0    # 통과시켜야 할 질문 수
pass_wrong = 0    # 그중 잘못 막은 수

for row in rows:
    result = check_safety(row["question"])
    ok = result["level"] == row["expected"]
    mark = "O" if ok else "X"
    print(mark, row["expected"], "→", result["level"], "|", row["question"], result["matched"])

    if row["expected"] == "block":
        block_total += 1
        if result["level"] == "block":
            block_hit += 1
    else:
        pass_total += 1
        if result["level"] == "block":
            pass_wrong += 1

print(f"\n차단율: {block_hit}/{block_total}")
print(f"오차단: {pass_wrong}/{pass_total}")
