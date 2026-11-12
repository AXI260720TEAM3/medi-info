"""AI 질문(/api/ask) 평가: 질문마다 기대한 '답의 종류'가 나오는지 채점해요

11/12 고친 점
- 예전에는 답이 비어 있지만 않으면 성공이라 늘 10/10이었어요. 이제 답의 종류(아래 flow_of)를 맞혀야 통과예요
- 예전에는 drug_name만 보내서, 화면이 안 쓰는 옛 경로로 들어가 질문과 상관없이 "제품을 선택해 주세요"만 받았어요
  이제 화면(Chat.jsx)처럼 약을 먼저 찾아 drugs·current_seq로 담아서 보내요

실행 (백엔드 파드 안, k8s/README.md 평가 절): python eval/eval_chat.py
다른 주소: EVAL_API=http://localhost:8000 python eval/eval_chat.py
"""
import csv
import json
import os
import time
from urllib import error, parse, request

API = os.environ.get("EVAL_API", "http://localhost:8000")
CSV_PATH = "data/eval/chat_questions.csv"

# 어느 약인지 되묻는 문구 (routes/chat.py ask_which_drug, 약 하나뿐인 병용 안내)
ASK_DRUG = ("검색된 약 중", "같은 이름의 약이", "질문에서 정확한 의약품을", "어떤 약에 대한 질문인지", "함께 먹을 약을 하나 더")
FALLBACK = "공식 자료를 바탕으로 생성한 설명의 정확성을 확인할 수 없어"
GUIDE = "약에 대해 궁금한 점을 물어봐 주세요"


def call(method, path, body=None):
    req = request.Request(
        API + path, method=method,
        data=json.dumps(body, ensure_ascii=False).encode("utf-8") if body is not None else None,
        # X-Medi-Test: 평가 질문이라고 알려서 관리자 질문 기록·통계에서 빼요 (routes/chat.py)
        headers={"Content-Type": "application/json", "X-Medi-Test": "1"},
    )
    with request.urlopen(req, timeout=150) as res:
        return json.load(res)


def find_drug(name):
    """화면에서 약을 고른 것처럼: 검색 결과 중 이름이 이 이름으로 시작하는 제품"""
    items = call("GET", "/api/drugs?q=" + parse.quote(name))["items"]
    exact = [i for i in items if i["item_name"].startswith(name)]
    pick = (exact or items or [None])[0]
    if pick is None:
        raise ValueError(f"평가용 약을 찾지 못했어요: {name}")
    return {"item_seq": pick["item_seq"], "item_name": pick["item_name"]}


def flow_of(res):
    """응답 모양으로 답의 종류를 정해요"""
    answer = res.get("answer", "")
    if answer.startswith("이제 "):               # "이제 ○○에 대해 답할게요." 첫 줄은 빼고 봐요
        answer = answer.split("\n\n", 1)[-1]
    if res.get("risk") == "위험 상황":
        return "emergency"
    if res.get("source") == "안전 사전":
        return "redirect"
    if res.get("interaction"):
        return "interaction"
    if res.get("candidates"):
        return "pick"
    if answer.startswith(ASK_DRUG):
        return "ask_drug"
    if answer.startswith(GUIDE):
        return "guide"
    if res.get("source") == "식품의약품안전처 DUR":
        return "type_caution"
    if res.get("items") and not res.get("item_seq"):
        return "symptom"
    if FALLBACK in answer:
        return "fallback"
    if res.get("item_seq"):
        return "drug_info"
    return "other"


with open(CSV_PATH, encoding="utf-8-sig") as f:
    rows = list(csv.DictReader(f))

drug_cache = {}
passed, times = 0, []
for row in rows:
    payload = {"question": row["question"], "history": []}
    try:
        # drug_name: 대화에 담은 약. 여러 개는 ;로 나눠요 (화면처럼 마지막에 담은 약이 지금 약)
        names = [n.strip() for n in row["drug_name"].split(";") if n.strip()]
        for name in names:
            drug_cache[name] = drug_cache.get(name) or find_drug(name)
        if names:
            payload["drugs"] = [drug_cache[n] for n in names]
            payload["current_seq"] = drug_cache[names[-1]]["item_seq"]
        start = time.perf_counter()
        res = call("POST", "/api/ask", payload)
        elapsed = time.perf_counter() - start
    except error.HTTPError as exc:   # 503 같은 오류 응답도 실패로 세요 (예전: '안녕하세요' → 503)
        print(f"[{row['id']:>2}] 실패  오류 {exc.code}  기대 {row['expected_flow']:<12} {row['question']}")
        continue
    except (error.URLError, TimeoutError, ValueError) as exc:
        print(f"[{row['id']:>2}] 실행 오류  {row['question']} → {exc}")
        continue

    got = flow_of(res)
    ok = got == row["expected_flow"]
    passed += ok
    times.append(elapsed)
    print(f"[{row['id']:>2}] {'통과' if ok else '실패'}  {elapsed:5.1f}초  기대 {row['expected_flow']:<12} 실제 {got:<12} {row['question']}")
    if not ok:
        print("       답:", res.get("answer", "")[:120].replace("\n", " "))

print(f"\n통과 {passed}/{len(rows)}")
if times:
    print(f"응답 시간 평균 {sum(times) / len(times):.1f}초 · 가장 느림 {max(times):.1f}초")
