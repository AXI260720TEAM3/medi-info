"""식약처 DUR 원문을 모아 용어 풀이 평가에 쓸 data/eval/dur_texts.csv를 만든다.

임부, 소아, 노인은 전체를 받고, 병용금기는 행이 너무 많아서 쪽을 골고루 골라 받는다.
같은 원문은 한 줄로 합치고, 몇 개 품목에 나왔는지(일반의약품 품목 수 포함)를 함께 적는다.
실행: python scripts/collect_dur_texts.py  (프로젝트 폴더에서, .env의 DATA_GO_KR_KEY 필요)
"""
import csv
import os
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor

import httpx
from dotenv import load_dotenv

load_dotenv(".env")
KEY = os.getenv("DATA_GO_KR_KEY")
BASE = "https://apis.data.go.kr/1471000/DURPrdlstInfoService03/"
SOURCES = {
    "임부": BASE + "getPwnmTabooInfoList03",
    "소아": BASE + "getSpcifyAgrdeTabooInfoList03",
    "노인": BASE + "getOdsnAtentInfoList03",
    "병용금기": BASE + "getUsjntTabooInfoList03",
}
ROWS = 100
TABOO_PAGES = 300  # 병용금기 쪽 7,900여 개 중 고르게 고를 쪽 수
OUT = "data/eval/dur_texts.csv"


def fetch(url, page):
    params = {"serviceKey": KEY, "type": "json", "numOfRows": ROWS, "pageNo": page}
    for attempt in range(3):
        try:
            res = httpx.get(url, params=params, timeout=30)
            res.raise_for_status()
            body = res.json()["body"]
            return body.get("totalCount") or 0, body.get("items") or []
        except (httpx.HTTPError, ValueError, KeyError):
            time.sleep(2 * (attempt + 1))
    print("실패한 쪽:", url.rsplit("/", 1)[-1], page)
    return 0, []


def main():
    found = defaultdict(lambda: {"rows": 0, "otc_rows": 0})
    for source, url in SOURCES.items():
        total, first = fetch(url, 1)
        last = (total + ROWS - 1) // ROWS
        if source == "병용금기":
            step = max(last // TABOO_PAGES, 1)
            pages = list(range(1 + step, last + 1, step))[:TABOO_PAGES - 1]
        else:
            pages = list(range(2, last + 1))
        with ThreadPoolExecutor(max_workers=4) as pool:
            results = [first] + [items for _, items in pool.map(lambda p: fetch(url, p), pages)]
        count = 0
        for items in results:
            for item in items:
                text = (item.get("PROHBT_CONTENT") or "").strip(' "-')
                if not text:
                    continue
                row = found[(source, text)]
                row["rows"] += 1
                row["otc_rows"] += "일반" in (item.get("ETC_OTC_NAME") or item.get("ETC_OTC_CODE") or "")
                count += 1
        print(f"{source}: 전체 {total}행 중 {1 + len(pages)}쪽, 원문 있는 행 {count}개")

    with open(OUT, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["source", "text", "rows", "otc_rows"])
        for (source, text), row in sorted(found.items(), key=lambda kv: (kv[0][0], -kv[1]["rows"])):
            writer.writerow([source, text, row["rows"], row["otc_rows"]])
    print(f"서로 다른 원문 {len(found)}개를 {OUT}에 저장했어요")


if __name__ == "__main__":
    main()
