
import csv
import json
import time
from urllib import request, error

API_URL = "http://localhost:8000/api/ask"
CSV_PATH = "data/eval/chat_questions.csv"

with open(CSV_PATH, encoding="utf-8-sig") as f:
    questions = list(csv.DictReader(f))

success = 0

for row in questions:
    payload = {"question": row["question"]}

    if row["drug_name"]:
        payload["drug_name"] = row["drug_name"]

    req = request.Request(
        API_URL,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    start = time.perf_counter()

    try:
        with request.urlopen(req, timeout=150) as response:
            result = json.load(response)

        elapsed = round((time.perf_counter() - start) * 1000)
        answer = result.get("answer", "")
        valid = isinstance(answer, str) and bool(answer.strip())

        if valid:
            success += 1

        print(f"\n[문제 {row['id']}] {'응답 성공' if valid else '빈 답변'}")
        print("질문:", row["question"])
        print("예상 흐름:", row["expected_flow"])
        print("출처:", result.get("source", "없음"))
        print("분류:", result.get("category", "없음"))
        print("응답 시간:", elapsed, "ms")
        print("답변:", str(answer)[:200])

    except (error.URLError, TimeoutError, ValueError) as exc:
        print(f"\n[문제 {row['id']}] 실행 오류: {exc}")

print(f"\n응답 성공: {success}/{len(questions)}")
