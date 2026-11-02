import csv
import sys

from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, "backend")

from app.services.safety import find_banned

with open("data/eval/banned_answers.csv", encoding="utf-8-sig") as f:
    rows = list(csv.DictReader(f))

ban_total = 0   # 잡아야 할 답변 수
ban_hit = 0     # 그중 실제로 잡은 수
ok_total = 0    # 그대로 보여 줘야 할 답변 수
wrong_ban = 0   # 그중 잘못 잡은 수

for row in rows:
    found = find_banned(row["answer"])
    expected = row["expected"]
    level = "ban" if found else "ok"
    mark = "O" if level == expected else "X"
    print(mark, expected, "→", level, "|", row["answer"], found)

    if expected == "ban":
        ban_total += 1
        if found:
            ban_hit += 1
    else:
        ok_total += 1
        if found:
            wrong_ban += 1

print(f"\n검출률: {ban_hit}/{ban_total}")
print(f"오검출: {wrong_ban}/{ok_total}")
