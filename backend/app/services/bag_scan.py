"""약봉지 사진 읽기: 비전 모델이 약 이름을 읽고, 허가정보에서 진짜 약을 찾아 후보로 돌려준다.

모델은 글자를 잘못 읽거나(계보린정), 표기를 바꾸거나(밀리그람 → 밀리그램), 잘린 이름을 읽을 수 있다.
그래서 읽은 이름을 그대로 쓰지 않고 허가정보에서 찾은 약만 후보로 보여 주고, 사용자가 골라야 내 약에 넣는다.
사진은 저장하지 않는다.
"""
import base64
import difflib
import os
import re
from concurrent.futures import ThreadPoolExecutor

import httpx

from ..config import OLLAMA_URL
from .permit_api import search_permit, search_withdrawn

VISION_MODEL = os.getenv("VISION_MODEL") or "qwen2.5vl:7b"  # .env에 빈칸으로 두어도 기본값을 쓴다
PROMPT = (
    "이 약봉지 사진에 적힌 약품명(제품 이름)만 한 줄에 하나씩 적어줘. "
    "약품명은 보통 정, 캡슐, 시럽, 액처럼 제형으로 끝나고 뒤에 용량이 붙기도 해. "
    "효능 분류(예: [항생제], [소염진통제]), 성분명, 모양 설명, 복용법은 적지 마. "
    "안 보이면 지어내지 말고 '모름'이라고 해."
)
# 약품명은 제형으로 끝난다 (뒤에 용량이 붙을 수 있다). '페니실린계 항생제' 같은 효능 분류를 걸러 낸다
NAME_END = re.compile(
    r"(정|캡슐|캡셀|캅셀|캅슐|시럽|액|산|과립|주|좌제|좌약|연고|크림|겔|로션|패취|패치|스프레이|점안액|점비액|트로키|츄어블)"
    r"\s*[\d.,/]*\s*(mg|밀리그램|밀리그람|밀리|밀|g|그램|ml|밀리리터|mcg|마이크로그램|%|IU|아이유|…|\.\.\.)?\s*$",
    re.IGNORECASE,
)
# 모양 설명(흰색 서방정, 흰색의 원형 정제), 효능 분류(항히스타민/항소양제)에 나오는 글자
DESCRIPTION = re.compile(r"색\s|색의|원형|타원형|장방형|분할선|경질캡슐$|[/&\[\]]")
MAX_IMAGE_BYTES = 8 * 1024 * 1024
MAX_NAMES = 15  # 같은 줄을 끝없이 반복할 때가 있어 읽은 이름 수를 제한한다
TOP = 3


class BadImage(ValueError):
    pass


def decode_image(data: str) -> str:
    """'data:image/png;base64,...' 또는 base64 글자를 받아 확인하고 base64 글자만 돌려준다."""
    data = data.split(",", 1)[1] if data.startswith("data:") else data
    try:
        raw = base64.b64decode(data, validate=True)
    except ValueError:
        raise BadImage("사진 파일을 읽지 못했어요.")
    if len(raw) > MAX_IMAGE_BYTES:
        raise BadImage("사진이 너무 커요. 8MB 이하로 올려 주세요.")
    if not (raw.startswith(b"\xff\xd8") or raw.startswith(b"\x89PNG")):
        raise BadImage("JPG나 PNG 사진만 올릴 수 있어요.")
    return data


def looks_like_name(line: str) -> bool:
    """약품명처럼 생겼는지: 제형으로 끝나고, 모양 설명이나 효능 분류 글자가 없다.
    '슈가메트서방정5/100…'처럼 잘린 이름은 '/'가 있어도 제형 뒤 용량이라 통과시킨다."""
    head = re.split(r"(?<=[가-힣])[\d.]", line, maxsplit=1)[0]  # 용량 앞까지 (슈가메트서방정)
    return bool(NAME_END.search(line)) and not DESCRIPTION.search(head)


def read_names(image: str) -> list[str]:
    """비전 모델이 사진에서 읽은 약 이름들. 같은 이름은 한 번만."""
    res = httpx.post(f"{OLLAMA_URL}/api/generate", timeout=120, json={
        "model": VISION_MODEL, "prompt": PROMPT, "images": [image], "stream": False,
        "options": {"temperature": 0, "num_predict": 300},
    })
    res.raise_for_status()
    names = []
    for line in re.split(r"[\n,]", res.json()["response"]):  # 한 줄에 쉼표로 이어 쓸 때도 있다
        line = re.sub(r"^\s*(\d+[.)]|[-*•])\s*", "", line).strip()  # 앞의 번호나 기호를 지운다
        line = re.sub(r"[_(].*$", "", line).strip(" *_")  # '*코푸시럽_(0.2g,3mg)' -> '코푸시럽' (약국이 붙인 표시와 성분 용량)
        if not line or line == "모름" or line.endswith(":") or len(line) > 40:  # 머리말과 문장은 뺀다
            continue
        if not looks_like_name(line):
            continue
        if line not in names:
            names.append(line)
    return names[:MAX_NAMES]


def _base(item_name):
    return item_name.split("(")[0].strip()


def _key(name):
    """비교용: 띄어쓰기를 지우고 mg, 밀리그램, 밀리그람을 같게 본다."""
    return re.sub(r"\s", "", name).replace("밀리그람", "mg").replace("밀리그램", "mg")


FORMS = ("서방정", "장용정", "연질캡슐", "캡슐", "정", "시럽", "현탁액", "액", "산", "과립", "좌약", "패취")


def _core(read):
    """제형(정, 캡슐 …)과 용량을 뺀 이름 부분. '캡슐300mg'처럼 이름이 가려진 줄은 빈 글자가 된다."""
    word = re.sub(r"[\d.,/]+\s*(mg|밀리그램|밀리그람|g|그램|ml|밀리리터)?", "", read.replace(" ", ""))
    for form in FORMS:
        if word.endswith(form):
            return word[: -len(form)]
    return word


def _queries(read):
    """찾아 볼 이름들. 뒷글자를 잘못 읽었을 때는 뒤를 줄이고, 앞글자를 잘못 읽었을 때는 앞을 뺀다."""
    out = [read, read.replace(" ", ""), read.replace("밀리그램", "밀리그람")]
    korean = re.match(r"[가-힣]+", read.replace(" ", ""))
    if korean:
        word = korean.group()
        out.append(word)
        out += [word[:n] for n in range(len(word) - 1, 1, -1)]
        out += [word[n:] for n in range(1, len(word) - 1)]
    return list(dict.fromkeys(q for q in out if len(q) >= 2 and q not in FORMS))  # '캡슐'만으로는 찾지 않는다


def match_name(read: str) -> dict:
    """읽은 이름 하나를 허가정보에서 찾는다.
    found: 표기만 다르고 이름이 같은 약이 하나 있음 / withdrawn: 허가가 취하된 약 /
    candidates: 비슷한 약 후보 / none: 못 찾음 / unchecked: 공공데이터 서버가 응답하지 않아 확인 못 함
    """
    if len(_core(read)) < 2:  # 이름 없이 제형과 용량만 읽었으면 찾지 않는다 (엉뚱한 약이 후보가 된다)
        return {"read": read, "status": "none", "candidates": []}
    found = {}
    failed = 0  # 공공데이터 서버가 느릴 때 몇 번 못 찾았는지. 일부가 실패해도 찾은 후보는 보여 준다
    for query in _queries(read):
        try:
            for drug in search_permit(query):
                found[drug["item_seq"]] = drug
        except httpx.HTTPError:
            failed += 1
            if failed >= 2:  # 서버가 느리면 계속 기다리지 않고 지금까지 찾은 후보만 쓴다
                break
            continue
        exact =[d for d in found.values() if _key(_base(d["item_name"])) == _key(read)]
        if len(exact) == 1:
            return {"read": read, "status": "found", "candidates": exact}
    if failed and not found:
        return {"read": read, "status": "unchecked", "candidates": []}
    # 판매 중인 약에 같은 이름이 없으면, 허가가 취하된 약인지 본다 (오래된 약봉지)
    try:
        withdrawn = [d for d in search_withdrawn(_core(read) or read) if _key(_base(d["item_name"])) == _key(read)]
    except httpx.HTTPError:
        withdrawn = []
    if withdrawn:
        return {"read": read, "status": "withdrawn", "candidates": [], "withdrawn": withdrawn[0]}
    ranked = sorted(found.values(),
                    key=lambda d: -difflib.SequenceMatcher(None, _key(read), _key(_base(d["item_name"]))).ratio())
    return {"read": read, "status": "candidates" if ranked else "none", "candidates": ranked[:TOP]}


def match_names(names: list[str]) -> list[dict]:
    """이름 하나에 허가정보를 여러 번 부르므로 4개씩 함께 찾는다."""
    with ThreadPoolExecutor(max_workers=4) as pool:
        return list(pool.map(match_name, names))
