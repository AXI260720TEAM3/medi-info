# ============================================================
# 파일명: chat_answer.py
# 역할: 공식 의약품 정보를 기반으로 AI 답변 생성 및 검증
#
# 주요 기능
# - _evidence(): 질문에 필요한 공식 자료 구성
# - _answer_from_official_info(): AI 답변 생성 및 재작성
# - 위험 표현, 숫자·용량, 복용 허가 표현 검증
# - 부적절한 답변 차단 및 안전한 안내 반환
#
# 연관 파일: routes/chat.py, chat_common.py, safety.py
# ============================================================

import logging
import re

from .chat_common import (
    SOURCE,
    DRUG_FIELDS,
    RELATED_FIELDS,
    ollama_generate,
)
from .safety import find_banned, find_unsupported_numbers

# 생성된 답변의 기계적 1차 검사: 의료적 정확성을 보증하지 않습니다.
DOSE_PATTERN = re.compile(
    # 11/11: "번"(하루 1~2번)이 없어서 지어낸 횟수가 검사를 지나갔어요. 허가정보의 전각 물결(60～120)도 함께
    r"\d+\s*(?:[~\-～〜]\s*\d+\s*)?(?:정|알|회|번|캡슐|포|mL|ml|mg|g)(?![A-Za-z0-9])",
    re.IGNORECASE,
)
UNSUPPORTED_DOSE = "공식 자료에 없는 용량·횟수 숫자"
UNSAFE_ASSURANCE = re.compile(
    r"무조건\s*(?:안전|괜찮)|절대\s*안전|"
    r"부작용(?:이|은)?\s*없(?:어|습니다)|"
    r"(?:함께|같이|추가로)\s*먹어도\s*(?:안전|괜찮)|"
    r"(?:누구나|모두)\s*(?:복용|먹어도)\s*(?:가능|괜찮)",
)
PERSONAL_APPROVAL = re.compile(
    r"(?:먹어도|복용해도)\s*(?:돼요|됩니다|괜찮아요)|"
    r"(?:복용|섭취)\s*(?:해도\s*)?(?:안전합니다|괜찮습니다)|"
    r"(?:반드시|문제없이)\s*복용(?:해도)?\s*(?:됩니다|가능합니다)|"
    r"(?:복용할|먹을|섭취할)\s*수\s*있(?:습니다|어요|지만|으나|고|다)(?![가-힣])|"
    r"(?:복용|섭취)(?:이|은)?\s*가능(?:합니다|해요|하지만|하나)"
)
DOSE_INTENT = re.compile(
    r"복용량|용량|용법|몇\s*(?:알|정|회|번)|"
    r"(?:하루|1일|일일)\s*몇|얼마나\s*(?:먹|복용)|"
    r"어떻게\s*(?:먹|복용)|복용\s*횟수|복용\s*간격",
    re.IGNORECASE,
)

HAN_PATTERN = re.compile(r"[\u4e00-\u9fff]")


def _evidence(drug: dict, categories: list[str]) -> str:
    return "\n".join(
        f"{name}: {drug.get(DRUG_FIELDS[name]) or '정보 없음'}"
        for name in dict.fromkeys(categories)
    )


def _answer_from_official_info(
    question: str,
    resolved_question: str,
    history: str,
    drug: dict,
    risk: str,
    category: str,
) -> str:

    personal = risk == "개인 복용 질문"

    # 개인 복용 질문의 연령 제한은 AI 추측보다 공식 자료를 우선
    if personal:
        age_text = question + "\n" + resolved_question

        user_ages = {
            int(age)
            for age in re.findall(
                r"(?<!\d)(\d{1,3})\s*(?:살|세)(?!\d)",
                age_text,
            )
        }

        if len(user_ages) == 1:
            user_age = next(iter(user_ages))

            official_text = "\n".join(
                str(drug.get(field) or "")
                for field in ("use_method", "atpn")
            )

            # 금지 문구가 있는 공식 자료의 문장만 확인
            sentences = re.split(
                r"(?<=[.!?])\s+|\n+",
                official_text,
            )

            for sentence in sentences:
                if not re.search(
                    r"복용하지\s*(?:마십시오|않는다|말\s*것|않아야)",
                    sentence,
                ):
                    continue

                limits = re.findall(
                    r"(?<!\d)(\d{1,3})\s*세\s*미만"
                    r"(?:의\s*(?:소아|어린이|아이|아동))?",
                    sentence,
                )

                for limit in limits:
                    limit_age = int(limit)

                    if user_age < limit_age:
                        return (
                            f"{drug['item_name']}의 공식 자료에는 "
                            f"{limit_age}세 미만은 복용하지 말라고 안내되어 있어요. "
                            f"{user_age}세는 이 기준에 해당하므로 "
                            "복용하지 마세요. "
                            "다른 약이 필요한 경우 의사 또는 약사와 상담해 주세요."
                        )

            # 연령별 복용 허가를 AI가 임의로 생성하지 않도록 방지
            if re.search(
                r"먹어도|복용해도|복용할\s*수|복용\s*가능",
                age_text,
            ):
                return (
                    f"{drug['item_name']}의 공식 자료만으로는 "
                    f"{user_age}세의 개인별 복용 가능 여부를 "
                    "확정하기 어려워요. "
                    "복용하기 전에 의사 또는 약사에게 확인해 주세요."
                )

    # 개인 복용 질문에서 알약 분할 여부를 확인
    split_question = bool(
        re.search(
            r"쪼개|분할|반으로|반\s*알|나눠|나누어",
            question + "\n" + resolved_question,
        )
    )

    if personal and split_question:
        official_text = " ".join(
            str(drug.get(field) or "")
            for field in ("use_method", "atpn_warn", "atpn")
        )

        has_split_guidance = bool(
            re.search(
                r"쪼개|분할|반으로|반\s*알|나눠|나누어",
                official_text,
            )
        )

        if not has_split_guidance:
            return (
                f"{drug['item_name']}을 반으로 나눠 복용해도 되는지는 "
                "현재 확인한 공식 자료에 명확한 안내가 없어 판단하기 어려워요. "
                "임의로 나눠 복용하기 전에 의사 또는 약사에게 확인해 주세요."
            )

    if personal:
        # 개인 질문은 관련 용법 및 주의·상담 항목을 항상 함께 참고합니다.
        fields = list(dict.fromkeys(
            RELATED_FIELDS.get(category, [])
            + ["복용방법", "복용 전 경고", "주의사항"]
        ))
    else:
        fields = RELATED_FIELDS[category]

    evidence = _evidence(drug, fields)

    evidence_source = (
        "식품의약품안전처 의약품 제품 허가정보"
        if drug.get("has_easy") is False
        else SOURCE
    )

    prompt = f"""당신은 식약처 의약품 정보를 일반인이 이해하도록 돕는 설명 도우미입니다.
[공식 자료]만 근거로 [현재 질문]에 직접 답하세요.
[이전 대화]와 [맥락을 반영한 질문]은 질문 의미를 이해하기 위한 자료이며 의료 사실을 입증하지 않습니다.

[반드시 지킬 규칙]
- 선택된 약은 '{drug['item_name']}'입니다. 다시 어떤 약인지 묻지 마세요.
- 사용자가 알려준 정보(예: 7살, 80살)를 존중하되 복용 가능 여부를 확정하지 마세요.
- '복용하지 마십시오'와 '의사·약사와 상의하십시오'는 뜻이 다릅니다. 섞어 쓰지 마세요.
- '만 2세 미만 상담'을 '만 2세부터 복용 가능'으로 바꾸지 마세요.
- 공식 자료에 정확한 최소 연령이 없으면 없다고 말하세요.
- 개인 질문에는 공식 자료의 관련 주의사항을 짧게 설명한 후 개인별 복용 허가는 판단하지 말고 약사·의사 확인을 안내하세요.
- 개인 질문에 대해서는 복용량·횟수·간격·정제 분할 허가를 절대 생성하지 마세요. 숫자로 된 용량도 쓰지 마세요.
- 일반적인 복용량 질문이라도 공식 자료의 범위를 넘지 마세요.
- 복용 연령 질문에 묻지 않은 성인 용량을 제시하지 마세요.
- 자료와 관련 없는 질환, 정보, 약 종류를 추가하지 마세요.
- 의학 용어와 전문적인 표현은 일반인이 이해하기 쉬운 일상적인 한국어로 풀어서 설명하세요.
- 어려운 표현을 그대로 반복하지 말고, 그 의미를 자연스럽고 간결하게 전달하세요.
- 단, 공식 자료의 의학적 의미, 수치, 연령 제한, 복용 금지, 주의 및 상담 필요 조건을 임의로 변경하거나 생략하지 마세요.
- 사용자가 묻지 않은 전문 용어나 주의사항을 불필요하게 나열하지 마세요.
- 명확하고 자연스러운 한국어 2~3문장. 자료가 불충분하면 확인할 수 없다고 말하세요.
- 공식 자료에 명시된 복용 금지, 주의, 상담 필요 조건은 의미와 강도를 그대로 유지하세요.
- 공식 자료에 없는 의학적 원인, 연령에 따른 신체 변화, 개인별 복용량 판단을 추측하여 설명하지 마세요.

[질문 위험 유형]
{risk}
[질문 정보 범주]
{category}
[선택된 제품]
{drug['item_name']}
[공식 자료 — {evidence_source}]
{evidence}
[이전 대화]
{history}
[맥락을 반영한 질문]
{resolved_question}
[현재 질문]
{question}
"""
    def rejection_reason(text: str) -> str | None:
        # 공식 자료의 연령별 복용 금지를 AI 답변이 누락했는지 검사
        if personal:
            caution = str(drug.get("atpn") or "")

            prohibited_under_ages = [
                int(age)
                for age in re.findall(
                    r"(\d{1,3})\s*세\s*미만[^.\n]{0,100}복용하지\s*마십시오",
                    caution,
                )
            ]

            mentioned_ages = {
                int(age)
                for age in re.findall(
                    r"(?<!\d)(\d{1,3})\s*(?:살|세)(?!\d)",
                    question + "\n" + resolved_question,
                )
            }

            if len(mentioned_ages) == 1 and prohibited_under_ages:
                user_age = next(iter(mentioned_ages))

                if any(user_age < limit for limit in prohibited_under_ages):
                    has_prohibition = re.search(
                        r"복용하지\s*마|복용하면\s*안|복용해서는\s*안"
                        r"|복용할\s*수\s*없|복용\s*금지",
                        text,
                    )

                    if not has_prohibition:
                        return "공식 자료에 명시된 연령별 복용 금지 안내 누락"
        if HAN_PATTERN.search(text):
            return "한자가 포함된 표현"

        if find_banned(text):
            return "약 추천·진단·안전 단정 등 금지 표현"

        if UNSAFE_ASSURANCE.search(text) or (personal and PERSONAL_APPROVAL.search(text)):
            return "복용 안전성을 단정하는 표현"

        if DOSE_PATTERN.search(text) and (personal or not DOSE_INTENT.search(question)):
            return "질문과 무관하거나 개인별 검증이 필요한 숫자·용량 표현"

        # 답의 용량·횟수·나이 숫자가 [공식 자료]·질문·약 이름에 없으면 AI가 지어낸 숫자 (safety.py, #102)
        # 용량을 물은 일반 질문이면 UNSUPPORTED_DOSE로 돌려줘서 "자료의 용법 문장을 옮겨 쓰라"는 재작성을 받게 해요
        allowed = "\n".join((evidence, drug["item_name"], question, resolved_question))
        if find_unsupported_numbers(text, allowed):
            if not personal and DOSE_INTENT.search(question):
                return UNSUPPORTED_DOSE
            return "공식 자료에 없는 숫자"

        return None

    answer = ollama_generate(prompt)
    reason = rejection_reason(answer)

    if reason is not None:
        logging.warning("AI 첫 답변 검증 실패: %s", reason)

    if reason is None:
        return answer

    # 오탐 가능성이 있는 첫 답변을 그대로 폐기하지 않고, 동일한 공식 자료에서
    # 불필요한 숫자·복용 허가를 제외하여 한 번만 재생성합니다.
    if reason == UNSUPPORTED_DOSE:
        # 용량을 물은 일반 질문: 숫자를 빼라고 하면 답이 비어요. 공식 자료의 용법 문장을 그대로 옮기게 해요
        repair_prompt = prompt + f"""

[재작성 지시]
앞선 초안이 다음 검증에 걸려 사용자에게 제공되지 않았습니다: {reason}.
[공식 자료]의 복용방법 문장에 적힌 숫자와 단위만 그대로 옮겨 쓰세요. 자료에 없는 숫자는 쓰지 마세요.
자료에서 찾을 수 없으면 확인할 수 없다고 말하세요. 자기 검증 과정에 관한 설명은 하지 마세요.
"""
        rewritten = ollama_generate(repair_prompt)
        rewrite_reason = rejection_reason(rewritten)
        if rewrite_reason is None:
            return rewritten
        logging.warning("AI 재생성 답변 검증 실패: %s", rewrite_reason)
        return (
            f"{drug['item_name']}의 공식 자료에서 질문하신 용법을 정확히 옮기지 못했어요. "
            "약 상세 화면의 '이렇게 먹어요'를 확인하시거나 약사에게 물어봐 주세요."
        )

    repair_prompt = prompt + f"""

[재작성 지시]
앞선 초안이 다음 검증에 걸려 사용자에게 제공되지 않았습니다: {reason}.
현재 질문에 관계없는 복용량·횟수·약의 함량 수치를 모두 제외하고,
공식 자료에 명시된 복용 금지 조건과 상담 필요 조건을 정확히 구분하여, 현재 질문에 해당하는 내용만 설명하세요.
사용자가 요청하지 않았다면 '상담 필요'와 '복용 금지'의 정의나 차이를 설명하지 마세요.
사용자에게 복용해도 된다는 허가나 구체적인 용량을 제시하지 마세요.
이미 선택된 제품을 다시 묻지 마세요. 자기 검증 과정에 관한 설명도 하지 마세요.
"""
    rewritten = ollama_generate(repair_prompt)
    rewrite_reason = rejection_reason(rewritten)

    if rewrite_reason is not None:
        logging.warning("AI 재생성 답변 검증 실패: %s", rewrite_reason)

    if rewrite_reason is None:
        return rewritten

    # 재생성도 부적합한 경우에는 AI 요약을 사용자에게 내보내지 않습니다.
    # 원본 공공 자료에 상담 안내가 실제로 있는 경우에 한해 그 문장을 그대로 표시합니다.
    if personal:
        # AI 답변이 검증에 실패해도 질문과 관련된 짧은 안내 제공
        is_split_question = bool(
            re.search(
                r"쪼개|분할|반으로|반\s*알|나눠|나누어",
                question + "\n" + resolved_question,
            )
        )

        if is_split_question:
            return (
                f"{drug['item_name']}을 반으로 나눠 복용해도 되는지는 "
                "현재 확인한 공식 자료만으로 안전하게 판단하기 어려워요. "
                "임의로 나눠 복용하기 전에 의사 또는 약사에게 확인해 주세요."
            )

        return (
            "현재 확인된 공식 자료만으로는 질문하신 상황에서 "
            "개인별 복용 가능 여부를 판단하기 어려워요. "
            "복용 전에 의사 또는 약사와 상담해 주세요."
        )
    return (
        "공식 자료를 바탕으로 생성한 설명의 정확성을 확인할 수 없어 "
        "답변을 표시하지 않았어요."
    )