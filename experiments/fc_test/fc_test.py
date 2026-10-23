"""
Function Calling 시험: qwen2.5가 질문을 보고 맞는 함수를 고르는지 확인한다.
(기술 스택 확정안 6장 "함수 고르기 시험" / 구현 기획 4장 AI 처리 흐름)

함수를 실제로 실행하지는 않는다. "어떤 함수를 어떤 인자로 부르려 하는지"만 본다.
실행: .venv/bin/python fc_test.py
"""
import json
import time

import requests

LLM_URL = 'http://localhost:11434/v1/chat/completions'
MODEL = 'qwen2.5:7b-instruct-q4_K_M'

SECTIONS = ['효능', '사용법', '주의사항', '상호작용', '부작용', '보관법']

# ---------------------------------------------------------------
# TODO 1. 함수 3개의 설명서(tool spec)를 만든다
#   - search_drug(name, section)  : 특정 약 하나에 대한 질문
#   - check_interaction(drugs)    : 약 2개 이상을 같이 먹어도 되는지
#   - list_by_efficacy(symptom)   : 증상으로 약 목록 찾기 (추천 아님)
# ---------------------------------------------------------------
TOOLS = [
    # 여기에 채우기
]

SYSTEM_PROMPT = """
"""  # TODO 2. 모델에게 줄 역할 설명 (짧게)


def ask(question):
    """질문 하나를 보내고 (함수 이름, 인자 dict) 또는 (None, 일반 답변)을 돌려준다."""
    # TODO 3. Ollama에 요청 보내기 (t01_llm_first_call.py + tools)
    # TODO 4. 응답에서 tool_calls 꺼내기
    pass


# 시험 질문: (질문, 기대하는 함수 이름). None = 함수를 부르지 않아야 함
CASES = [
    ('타이레놀 하루에 몇 번 먹어요?', 'search_drug'),
    ('게보린 부작용 뭐 있어요?', 'search_drug'),
    ('판콜에이 냉장고에 보관해야 돼요?', 'search_drug'),
    ('타이레놀이랑 판콜에이 같이 먹어도 돼요?', 'check_interaction'),
    ('게보린 먹고 있는데 탁센 또 먹어도 괜찮나요?', 'check_interaction'),
    ('부루펜하고 타이레놀 같이 먹으면 안 되나요?', 'check_interaction'),
    ('머리 아플 때 먹는 약 있어요?', 'list_by_efficacy'),
    ('속이 쓰려요, 무슨 약이 있나요?', 'list_by_efficacy'),
    ('콧물 멈추는 약 알려줘', 'list_by_efficacy'),
    ('오늘 날씨 어때?', None),
    ('안녕하세요', None),
]


if __name__ == '__main__':
    passed = 0
    for question, expected in CASES:
        start = time.time()
        name, args = ask(question)
        sec = time.time() - start

        ok = name == expected
        passed += ok
        mark = '✅' if ok else '❌'
        print(f'{mark} {sec:4.1f}s | {question}')
        print(f'      기대: {expected} / 결과: {name} {args}')

    print(f'\n정답률: {passed}/{len(CASES)}')
