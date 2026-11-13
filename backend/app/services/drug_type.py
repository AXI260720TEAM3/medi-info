"""약 이름 대신 '두통약', '감기약' 같은 약 종류로 물었을 때, 대표 성분의 식약처 DUR 주의 자료를 찾는다.

'임신했는데 두통약 먹어도 돼?' 처럼 제품 이름이 없으면 AI 질문은 어떤 약인지 되묻기만 했다 (11/12).
되묻기 전에 그 종류에 흔히 들어 있는 성분이 임부·소아·노인 DUR 자료에 있는지 먼저 보여 주려고 만든다.

- 약을 골라 주지 않는다. '이 성분은 식약처 자료에 이렇게 적혀 있다'만 돌려준다
- 판정과 근거는 코드가 정하고, AI는 이 결과로 설명만 한다 (함께 먹기와 같은 원칙)
- DUR 자료에 없는 성분도 안전하다는 뜻은 아니어서 notice로 함께 알린다
"""
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache

import httpx

from .dur_api import CAUTION_URLS, _call

# 약 종류 말 -> 그 종류의 일반의약품에 흔히 들어 있는 성분 (DUR 자료의 성분 이름 앞부분)
# 같은 종류를 부르는 다른 말은 같은 목록을 쓴다. 띄어쓰기를 지운 질문과 비교한다
PAIN = ("아세트아미노펜", "이부프로펜", "덱시부프로펜", "나프록센", "아스피린")
COLD = ("아세트아미노펜", "이부프로펜", "클로르페니라민", "슈도에페드린", "페닐레프린", "덱스트로메토르판", "구아이페네신")
ALLERGY = ("클로르페니라민", "세티리진", "로라타딘", "펙소페나딘", "슈도에페드린")
COUGH = ("덱스트로메토르판", "디히드로코데인", "구아이페네신")
SLEEP = ("디펜히드라민", "독실아민")
MOTION = ("디멘히드리네이트", "스코폴라민")

DRUG_TYPES = {
    "두통약": PAIN, "진통제": PAIN, "해열제": PAIN, "해열진통제": PAIN, "소염진통제": PAIN,
    "생리통약": PAIN, "치통약": PAIN, "몸살약": PAIN,
    "감기약": COLD, "종합감기약": COLD, "코감기약": COLD, "목감기약": COLD,
    "콧물약": ALLERGY, "비염약": ALLERGY, "알레르기약": ALLERGY, "알러지약": ALLERGY,
    "기침약": COUGH, "기침감기약": COUGH, "가래약": COUGH,
    "수면유도제": SLEEP, "수면보조제": SLEEP,
    "멀미약": MOTION,
}
# 긴 말부터 본다: '기침감기약'을 '감기약'보다 먼저
TYPE_WORDS = sorted(DRUG_TYPES, key=len, reverse=True)

# 약 종류 → e약은요 효능에서 찾을 말 (11/12): "해열제 알려줘"에 약 목록을 보여 주려고 (증상 질문의 목록과 같은 방식)
# 효능 검색으로 결과가 잘 나오는 말을 골랐어요 (예: '불면' 21개 = 독시라민 수면유도제, '해열' 101개)
TYPE_SYMPTOMS = {
    "두통약": "두통", "진통제": "두통", "해열진통제": "두통", "해열제": "해열", "소염진통제": "염좌",
    "생리통약": "생리통", "치통약": "치통", "몸살약": "근육통",
    "감기약": "감기", "종합감기약": "감기", "코감기약": "콧물", "목감기약": "인후통", "콧물약": "콧물",
    "비염약": "비염", "알레르기약": "알레르기", "알러지약": "알레르기",
    "기침약": "기침", "기침감기약": "기침", "가래약": "가래",
    "수면유도제": "불면", "수면보조제": "불면", "멀미약": "멀미",
}

NOTICE = (
    "약 종류에 흔히 들어 있는 성분만 확인했어요. 실제 약에는 다른 성분이 섞여 있을 수 있어요. "
    "식약처 DUR 자료에 없는 성분도 안전하다는 뜻은 아니에요."
)


def find_drug_type(question: str):
    """질문에 있는 약 종류 말을 돌려준다. 없으면 None. ('두통약 먹어도 돼?' -> '두통약')"""
    text = question.replace(" ", "")
    return next((word for word in TYPE_WORDS if word in text), None)


@lru_cache(maxsize=200)
def _ingredient_cautions(target: str, ingredient: str):
    """성분 하나의 DUR 주의 자료. 성분별 조회 서비스는 쓸 수 없어서, 제품 이름에 성분이 적힌 약으로 찾는다.

    제품 이름 검색이라 성분이 여러 개인 약도 섞여 나와서, 자료의 성분 이름이 이 성분인 줄만 남긴다.
    """
    rows = []
    for item in _call(CAUTION_URLS[target], {"itemName": ingredient}):
        if not (item.get("INGR_NAME") or "").startswith(ingredient):
            continue
        content = (item.get("PROHBT_CONTENT") or "").strip(' "-')
        row = {"type": item.get("TYPE_NAME") or target, "content": content}
        if row not in rows:
            rows.append(row)
    return tuple(rows[:2])  # 같은 성분은 내용이 거의 같아서 두 개면 충분하다


def _cautions_or_none(target: str, ingredient: str):
    try:
        return list(_ingredient_cautions(target, ingredient))
    except (httpx.HTTPError, ValueError, KeyError):
        return None


DUR_TARGETS = tuple(CAUTION_URLS)  # DUR 자료가 있는 주의 대상 (임부·소아·노인)
TARGET_NAMES = {"임부": "임신 중", "소아": "어린이", "노인": "어르신"}
# DUR 자료 종류를 쉬운 말로
TYPE_MEANINGS = {
    "임부금기": "임신 중에는 쓰지 않도록 식약처가 정한 성분",
    "특정연령대금기": "특정 나이에서는 쓰지 않거나 조심하도록 식약처가 정한 성분",
    "노인주의": "어르신이 쓸 때 주의하도록 식약처가 정한 성분",
}
ASK_NAME = "갖고 계신 약의 이름을 알려 주시면 그 약에 실제로 든 성분과 주의사항을 확인해 드릴게요."


def type_cautions_answer(result: dict) -> str:
    """type_cautions 결과로 AI 질문의 답을 만든다. AI를 부르지 않고 코드가 쓴다 (지어내지 않게, 빨리)

    약을 골라 주지 않는다: '이 성분을 드세요'가 아니라 'DUR 자료에 이렇게 있다/없다'만 적는다.
    """
    lines = [f"{result['drug_type']}에 흔히 들어 있는 성분을 식약처 DUR 자료에서 확인했어요."]
    for target in result["targets"]:
        listed, not_listed, failed = {}, [], []
        for row in result["ingredients"]:
            cautions = row["cautions"][target]
            if cautions is None:
                failed.append(row["ingredient"])
            elif cautions:
                listed.setdefault(cautions[0]["type"], []).append(row["ingredient"])
            else:
                not_listed.append(row["ingredient"])
        lines.append("")
        lines.append(f"[{TARGET_NAMES[target]}]")
        for caution_type, names in listed.items():
            meaning = TYPE_MEANINGS.get(caution_type)
            lines.append(f"- {caution_type}{f'({meaning})' if meaning else ''}: {', '.join(names)}")
        if not_listed:
            lines.append(f"- 식약처 DUR 주의 목록에 없는 성분: {', '.join(not_listed)}")
        if failed:
            lines.append(f"- 약 정보 서버가 느려서 확인하지 못함: {', '.join(failed)}")
    lines += ["", result["notice"], ASK_NAME]
    return "\n".join(lines)


def type_cautions(drug_type: str, targets: list):
    """약 종류의 대표 성분마다 주의 대상(임부·소아·노인)별 DUR 자료를 돌려준다.

    cautions[대상]: 자료 목록이면 DUR에 있음, 빈 목록이면 DUR에 없음, None이면 조회 실패(판단하지 않음).
    DUR 자료가 없는 대상(수유, 복용중)은 건너뛴다.
    """
    ingredients = DRUG_TYPES[drug_type]
    targets = [target for target in dict.fromkeys(targets) if target in CAUTION_URLS]
    jobs = [(target, ingredient) for ingredient in ingredients for target in targets]
    with ThreadPoolExecutor(max_workers=4) as pool:
        found = dict(zip(jobs, pool.map(lambda job: _cautions_or_none(*job), jobs)))
    return {
        "drug_type": drug_type,
        "targets": targets,
        "ingredients": [
            {"ingredient": ingredient, "cautions": {target: found[(target, ingredient)] for target in targets}}
            for ingredient in ingredients
        ],
        "notice": NOTICE,
        "source": "식약처 DUR",
    }
