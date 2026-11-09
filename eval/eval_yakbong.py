"""약봉지 읽기 평가: 비전 모델이 복약안내문 그림에서 약 이름을 정확히 읽는지 본다.

그림과 정답은 scripts/make_yakbong_samples.py로 만든 data/eval/yakbong_answers.csv를 쓴다.
맞힌 이름, 놓친 이름, 그림에 없는데 지어낸 이름을 센다. 띄어쓰기는 무시하고 비교한다.
서버와 같은 코드(backend/app/services/bag_scan.py의 read_names)로 읽어서, 지시문이나 거르는 규칙을 바꾸면 바로 점수에 나온다.
실행: python eval/eval_yakbong.py [모델 이름]  (Ollama가 켜져 있어야 함. 기본 http://localhost:11434)
"""
import base64
import csv
import os
import re
import sys
import time
from collections import defaultdict

import argparse

parser = argparse.ArgumentParser()
parser.add_argument("model", nargs="?", help="비전 모델 (기본: 서버와 같은 VISION_MODEL)")
parser.add_argument("--answers", default="data/eval/yakbong_answers.csv",
                    help="정답 파일. 실제 양식을 본뜬 그림은 data/eval/yakbong_layouts_answers.csv")
ARGS = parser.parse_args()
if ARGS.model:
    os.environ["VISION_MODEL"] = ARGS.model
os.environ.setdefault("OLLAMA_URL", "http://localhost:11434")
sys.path.insert(0, "backend")
from app.services import bag_scan  # noqa: E402  (위에서 정한 환경 변수를 읽는다)

ANSWERS = ARGS.answers
MODEL = bag_scan.VISION_MODEL


def read_names(path):
    with open(path, "rb") as f:
        return bag_scan.read_names(base64.b64encode(f.read()).decode())


def key(name):
    return re.sub(r"\s", "", name)


def same(answer, got):
    """정답이 '…'로 끝나면 그림에서 이름이 잘린 것이라 앞부분만 맞으면 된다."""
    a, g = key(answer), key(got)
    return g.startswith(a[:-1]) if a.endswith("…") else a == g


def main():
    rows = list(csv.DictReader(open(ANSWERS, encoding="utf-8")))
    stat = defaultdict(lambda: [0, 0, 0, 0, 0.0])  # 정답 이름 수, 맞힘, 지어냄, 그림 수, 걸린 시간
    print(f"모델 {MODEL}, 그림 {len(rows)}장\n")
    for row in rows:
        answer = row["names"].split("|")
        start = time.time()
        got = read_names(row["file"])
        took = time.time() - start
        hit = [n for n in answer if any(same(n, g) for g in got)]
        missed = [n for n in answer if n not in hit]
        extra = [g for g in got if not any(same(n, g) for n in answer)]
        group = f"{row['layout']}/{row['variant']}" if row.get("layout") else row["variant"]
        for name in (group, "전체"):
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
