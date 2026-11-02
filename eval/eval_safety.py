import csv
import sys

from dotenv import load_dotenv

load_dotenv()                 # ① .env → 환경변수
sys.path.insert(0, "backend") # ② backend 폴더에서 app을 찾게

from app.services.safety import check_safety  # ③ 이제 불러와도 안전

with open("data/eval/safety_questions.csv", encoding="utf-8-sig") as f:
    rows = list(csv.DictReader(f))

block_total = 0     # 막아야 할 질문 수
block_hit = 0       # 그중 실제로 막은 수
redirect_total = 0  # 전환해야 할 질문 수
redirect_hit = 0    # 그중 실제로 전환한 수
pass_total = 0      # 통과시켜야 할 질문 수
pass_redirect = 0   # 그중 잘못 전환한 수
wrong_block = 0     # 막으면 안 되는데 막은 수
warn_total = 0      # 주의를 줘야 할 질문 수
warn_hit = 0        # 그중 실제로 주의를 준 수
pass_warn = 0       # 통과해야 하는데 주의를 준 수

for row in rows:
    result = check_safety(row["question"])
    expected = row["expected"]
    level = result["level"]
    mark = "O" if level == expected else "X"
    print(mark, expected, "→", level, "|", row["question"], result["matched"])

    if expected == "block":
        block_total += 1
        if level == "block":
            block_hit += 1
    elif expected == "redirect":
        redirect_total += 1
        if level == "redirect":
            redirect_hit += 1
    elif expected == "warn":
        warn_total += 1
        if level == "warn":
            warn_hit += 1
    else:
        pass_total += 1
        if level == "redirect":
            pass_redirect += 1
        if level == "warn":
            pass_warn += 1

    if expected != "block" and level == "block":
        wrong_block += 1

print(f"\n차단율: {block_hit}/{block_total}")
print(f"오차단: {wrong_block}/{redirect_total + warn_total + pass_total}")
print(f"전환율: {redirect_hit}/{redirect_total}")
print(f"오전환: {pass_redirect}/{pass_total}")
print(f"경고율: {warn_hit}/{warn_total}")
print(f"오경고: {pass_warn}/{pass_total}")
