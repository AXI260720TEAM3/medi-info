"""약봉지 읽기 평가: 비전 모델이 복약안내문 그림에서 약 이름을 정확히 읽는지 본다.

그림과 정답은 scripts/make_yakbong_samples.py로 만든 data/eval/yakbong_answers.csv를 쓴다.
맞힌 이름, 놓친 이름, 그림에 없는데 지어낸 이름을 센다. 띄어쓰기는 무시하고 비교한다.
실행: python eval/eval_yakbong.py [모델 이름]  (Ollama가 켜져 있어야 함)
"""
import base64
import csv
import os
import re
import sys
import time
from collections import defaultdict

import httpx

ANSWERS = "data/eval/yakbong_answers.csv"
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
MODEL = sys.argv[1] if len(sys.argv) > 1 else "qwen2.5vl:7b"
PROMPT = "이 약봉지 사진에 적힌 약 이름만 한 줄에 하나씩 적어줘. 안 보이면 지어내지 말고 '모름'이라고 해."


def read_names(path):
    with open(path, "rb") as f:
        image = base64.b64encode(f.read()).decode()
    res = httpx.post(f"{OLLAMA_URL}/api/generate", timeout=300, json={
        "model": MODEL, "prompt": PROMPT, "images": [image], "stream": False,
        "options": {"temperature": 0, "num_predict": 300},  # 같은 줄을 끝없이 반복할 때가 있어 길이를 제한한다
    })
    res.raise_for_status()
    names = []
    for line in re.split(r"[\n,]", res.json()["response"]):  # 한 줄에 쉼표로 이어 쓸 때도 있다
        line = re.sub(r"^\s*(\d+[.)]|[-*•])\s*", "", line).strip()  # 앞의 번호나 기호를 지운다
        if line and line != "모름" and not line.endswith((":", ".")):  # "약 이름은 다음과 같습니다:" 같은 머리말은 뺀다
            names.append(line)
    return names


def key(name):
    return re.sub(r"\s", "", name)


def main():
    rows = list(csv.DictReader(open(ANSWERS, encoding="utf-8")))
    stat = defaultdict(lambda: [0, 0, 0, 0, 0.0])  # 정답 이름 수, 맞힘, 지어냄, 그림 수, 걸린 시간
    print(f"모델 {MODEL}, 그림 {len(rows)}장\n")
    for row in rows:
        answer = row["names"].split("|")
        start = time.time()
        got = read_names(row["file"])
        took = time.time() - start
        hit = [n for n in answer if key(n) in {key(g) for g in got}]
        missed = [n for n in answer if n not in hit]
        extra = [g for g in got if key(g) not in {key(n) for n in answer}]
        for name in (row["variant"], "전체"):
            s = stat[name]
            s[0] += len(answer)
            s[1] += len(hit)
            s[2] += len(extra)
            s[3] += 1
            s[4] += took
        mark = "OK " if not missed and not extra else "XX "
        print(f"{mark}{row['file'].rsplit('/', 1)[-1]:<22} {len(hit)}/{len(answer)} {took:4.1f}초", end="")
        if missed:
            print(f"  놓침: {', '.join(missed)}", end="")
        if extra:
            print(f"  잘못 읽음: {', '.join(extra)}", end="")
        print()

    print("\n종류        맞힌 이름          지어내거나 틀린 이름  한 장 평균")
    for name, (total, hit, extra, count, took) in stat.items():
        print(f"{name:<10} {hit:>3}/{total:<3} ({hit / total:6.1%})   {extra:>3}개              {took / count:4.1f}초")


if __name__ == "__main__":
    main()
