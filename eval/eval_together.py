import csv
import sys

from dotenv import load_dotenv

load_dotenv()                 # ① .env → 환경변수
sys.path.insert(0, "backend") # ② backend 폴더에서 app을 찾게

from app.services.dur_api import check_interaction  # ③ 이제 불러와도 안전

PATH = sys.argv[1] if len(sys.argv) > 1 else "data/eval/together_pairs.csv"
SERVER_DOWN = "응답하지 않아"

with open(PATH, encoding="utf-8-sig") as f:
    rows = list(csv.DictReader(f))

total = {"block": 0, "warn": 0, "pass": 0, "unknown": 0}
hit = {"block": 0, "warn": 0, "pass": 0, "unknown": 0}
missed = []       # 문제가 있는 조합인데 pass로 답한 것
server_down = []  # 서버가 응답하지 않아 판정을 믿을 수 없는 것

for row in rows:
    expected = row["expected"]
    result = check_interaction([row["item_seq_a"], row["item_seq_b"]])[0]
    level = result["level"]
    name = f"{row['name_a']} + {row['name_b']}"

    if any(SERVER_DOWN in reason for reason in result["reasons"]):
        server_down.append(name)

    mark = "O" if level == expected else "X"
    print(mark, expected, "→", level, "|", name, "|", row["memo"], flush=True)

    total[expected] += 1
    if level == expected:
        hit[expected] += 1
    if expected != "pass" and level == "pass":
        missed.append(name)

print(f"\n판정 정확도: {sum(hit.values())}/{len(rows)}")
print(f"금기 적중: {hit['block']}/{total['block']}")
print(f"주의 적중: {hit['warn']}/{total['warn']}")
print(f"통과 적중: {hit['pass']}/{total['pass']}")
print(f"확인 불가 적중: {hit['unknown']}/{total['unknown']}")
print(f"문제 있는 조합을 pass로 답함: {len(missed)}/{len(rows) - total['pass']}")
for name in missed:
    print("-", name)
print(f"서버 응답 없음: {len(server_down)}/{len(rows)} (이 조합의 판정은 믿을 수 없어요. 다시 돌려 주세요)")
for name in server_down:
    print("-", name)
