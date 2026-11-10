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
from .query_ai import parse_query
from .search import find_drug


def find_chat_drug(question: str) -> dict:
    """기존 약 검색을 유지하고, 검색 실패 시 허가정보까지 확인."""

    result = find_drug(question)

    if not isinstance(result, dict):
        raise ValueError("약 검색 결과 형식이 올바르지 않습니다.")

    if result.get("status") in ("found", "ambiguous"):
        return result

    name = (parse_query(question).get("drug_name") or "").strip()

    if not name:
        return {"status": "none"}

    _, items = search_merged(name, page=1, size=20)

    if not items:
        return {"status": "none"}

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


def get_chat_drug_detail(item_seq: str) -> dict | None:
    """e약은요 우선 조회, 없으면 의약품 제품 허가정보 조회."""

    drug = get_by_seq(item_seq)

    if drug is not None:
        return drug

    return get_permit_detail(item_seq)