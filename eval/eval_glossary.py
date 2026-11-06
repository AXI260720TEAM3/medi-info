"""용어 풀이 평가: 식약처 DUR 원문 중 풀이가 붙는 비율과, 아직 풀이가 없는 자주 나오는 말을 보여 준다.

원문은 scripts/collect_dur_texts.py로 모은 data/eval/dur_texts.csv를 쓴다.
풀이 찾는 방법은 화면(TermNotes.jsx)과 같다: 띄어쓰기를 지운 원문에 words가 들어 있으면 풀이를 붙인다.
실행: python eval/eval_glossary.py
"""
import csv
import json
import re
from collections import Counter, defaultdict

GLOSSARY = "frontend/src/data/glossary.json"
TEXTS = "data/eval/dur_texts.csv"
JOSA = re.compile(r"(으로|에서|에게|과의|와의|이며|이고|으며|하여|되어|된|되는|하는|한|의|을|를|이|가|은|는|과|와|에|로|도|및)$")
SHORT = 2  # 이 글자 수 이하의 표기는 다른 낱말 안에서 잘못 찾을 수 있어 앞뒤를 보여 준다


def has_term(entry, joined):
    for word in entry.get("except", []):  # 표기가 들어 있지만 뜻이 다른 낱말 (예: 경구개)
        joined = joined.replace(word, " ")
    return any(word in joined for word in entry["words"])


def found_terms(text, glossary):
    joined = re.sub(r"\s", "", text)
    return [e["term"] for e in glossary if has_term(e, joined)]


def main():
    glossary = json.load(open(GLOSSARY, encoding="utf-8"))
    rows = list(csv.DictReader(open(TEXTS, encoding="utf-8")))

    covered = defaultdict(lambda: [0, 0, 0, 0])  # 원문 수, 풀이 붙은 원문 수, 품목 행 수, 풀이 붙은 행 수
    used = Counter()
    uncovered = Counter()
    for row in rows:
        terms = found_terms(row["text"], glossary)
        used.update(terms)
        rows_n = int(row["rows"])
        for key in (row["source"], "전체"):
            stat = covered[key]
            stat[0] += 1
            stat[1] += bool(terms)
            stat[2] += rows_n
            stat[3] += rows_n * bool(terms)
        # 풀이 단어와 겹치지 않는 낱말 중 자주 나오는 것 (다음에 넣을 후보)
        joined_words = [w for e in glossary for w in e["words"]]
        for token in set(re.findall(r"[가-힣A-Za-z]+", row["text"])):
            token = JOSA.sub("", token)
            if len(token) >= 2 and not any(w in token or token in w for w in joined_words):
                uncovered[token] += 1

    print(f"풀이 {len(glossary)}개, 원문 {len(rows)}개\n")
    print("출처      풀이가 붙은 원문        풀이가 붙은 품목 행")
    for key, (n, hit, rows_n, rows_hit) in covered.items():
        print(f"{key:<6} {hit:>4}/{n:<4} ({hit / n:6.1%})   {rows_hit:>6}/{rows_n:<6} ({rows_hit / rows_n:6.1%})")

    never = [e["term"] for e in glossary if used[e["term"]] == 0]
    print(f"\n원문에 한 번도 안 나온 풀이 {len(never)}개: {', '.join(never)}")

    print("\n짧은 표기가 들어간 낱말 (잘못 찾는지 확인)")
    for entry in glossary:
        for word in entry["words"]:
            if len(word) > SHORT:
                continue
            contexts = Counter()
            for row in rows:
                for token in re.findall(r"[가-힣A-Za-z]+", row["text"]):
                    if has_term({"words": [word], "except": entry.get("except", [])}, token):
                        contexts[token] += 1
            print(f"  {word}: {', '.join(t for t, _ in contexts.most_common(12))}")

    print("\n풀이가 없는 자주 나오는 낱말 (원문 수)")
    print(" ".join(f"{w}:{n}" for w, n in uncovered.most_common(80)))


if __name__ == "__main__":
    main()
