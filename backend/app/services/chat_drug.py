# ============================================================
# 파일명: chat_drug.py
# 역할: AI 채팅에서 사용할 의약품 검색 및 상세정보 조회
#
# 주요 기능
# - find_chat_drug(): 일반·전문의약품 검색 및 후보 확인
# - get_chat_drug_detail(): e약은요 또는 허가정보 상세 조회
#
# 연관 파일: routes/chat.py
# ============================================================

import re

from .drug_api import get_by_seq
from .drug_search import search_merged
from .permit_api import get_permit_detail
from .search import find_drug


def find_chat_drug(question: str) -> dict:
    """기존 약 검색을 유지하고, 검색 실패 시 허가정보까지 확인."""

    result = find_drug(question)

    if not isinstance(result, dict):
        raise ValueError("약 검색 결과 형식이 올바르지 않습니다.")

    if result.get("status") in ("found", "ambiguous"):
        return result

    # find_drug가 이미 질문에서 약 이름을 뽑았어요 (못 뽑았으면 name이 없음).
    # parse_query를 다시 부르면 약 이름이 없는 질문마다 AI를 한 번 더 불러 1~2초 느려져요 (11/10)
    name = (result.get("name") or "").strip()

    if not name:
        return {"status": "none"}

    _, items = search_merged(name, page=1, size=20)

    if not items:
        # 이름은 적었는데 못 찾음: 화면이 "정확한 의약품을 찾지 못했어요"로 안내할 수 있게 이름을 남겨요
        return {"status": "none", "name": name}

    normalized = re.sub(r"\s+", "", name).lower()

    exact = [
        item for item in items
        if re.sub(
            r"\s+", "",
            str(item.get("item_name", "")).split("(")[0]
        ).lower() == normalized
    ]

    if len(exact) == 1:
        return {"status": "found", "drug": exact[0]}

    return {
        "status": "ambiguous",
        "name": name,
        "candidates": items,
    }


# 허가정보 주의사항은 번호 문단 하나에 경고·함께 먹으면 안 되는 약·복용 중지 증상이 섞여 있어요.
# 머리말("1. 경고", "3. ... 다음의 약을 복용하지 말 것", "6. ... 즉각 중지하고 ...")에 이 말이 있으면
# 그 문단을 e약은요의 같은 칸에 옮겨 담아요. 그러면 답변 코드(chat_answer.py)는 e약은요 약과 똑같이 동작해요 (11/10)
PERMIT_SECTION_WORDS = {
    "atpn_warn": ("경고",),
    "intrc": ("다음의 약", "병용", "상호작용"),
    "se": ("즉각 중지", "즉시 중지", "이상반응", "부작용"),
}
# 전문의약품 원문은 1만 자가 넘기도 해요. AI가 읽을 수 있는 길이를 넘으면
# Ollama가 프롬프트 앞부분(안전 규칙)부터 조용히 버려서, 칸마다 이 길이까지만 넣어요
PERMIT_FIELD_LIMIT = 4000
PERMIT_SECTION_HEAD = re.compile(r"^\s*\d{1,2}\.\s")


def _permit_sections(text: str) -> list[tuple[str, str]]:
    """허가정보 주의사항을 (머리말, 문단 전체) 목록으로. 번호 문단이 없으면 빈 목록"""
    sections = []
    for line in text.split("\n"):
        if PERMIT_SECTION_HEAD.match(line):
            sections.append([line.strip(), line])
        elif sections:
            sections[-1][1] += "\n" + line
    return [(head, body.strip()) for head, body in sections]


def _clip(text: str) -> str:
    if len(text) <= PERMIT_FIELD_LIMIT:
        return text
    return text[:PERMIT_FIELD_LIMIT] + "\n… (이하 생략: 약 상세 화면에서 전체를 볼 수 있어요)"


def _with_easy_fields(drug: dict) -> dict:
    """허가정보로 찾은 약을 e약은요 칸 모양으로 맞춰요 (빈 칸만 채우고, 긴 글은 잘라요)"""
    drug = dict(drug)
    sections = _permit_sections(str(drug.get("atpn") or ""))
    for key, words in PERMIT_SECTION_WORDS.items():
        if not drug.get(key):
            picked = [body for head, body in sections if any(word in head for word in words)]
            drug[key] = _clip("\n".join(picked)) if picked else None
    for key in ("efcy", "use_method", "atpn", "deposit"):
        if drug.get(key):
            drug[key] = _clip(str(drug[key]))
    return drug


def get_chat_drug_detail(item_seq: str) -> dict | None:
    """e약은요 우선 조회, 없으면 의약품 제품 허가정보 조회."""

    drug = get_by_seq(item_seq)

    if drug is not None:
        return drug

    drug = get_permit_detail(item_seq)
    return _with_easy_fields(drug) if drug else None