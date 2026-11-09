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
PROMPT = "이 약봉지 사진에 적힌 약 이름만 한 줄에 하나씩 적어줘. 안 보이면 지어내지 말고 '모름'이라고 해."
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
        if not line or line == "모름" or line.endswith((":", ".")) or len(line) > 40:  # "다음과 같습니다." 같은 머리말과 문장은 뺀다
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
    candidates: 비슷한 약 후보 / none: 못 찾음
    """
    if len(_core(read)) < 2:  # 이름 없이 제형과 용량만 읽었으면 찾지 않는다 (엉뚱한 약이 후보가 된다)
        return {"read": read, "status": "none", "candidates": []}
    found = {}
    for query in _queries(read):
        for drug in search_permit(query):
            found[drug["item_seq"]] = drug
        exact = [d for d in found.values() if _key(_base(d["item_name"])) == _key(read)]
        if len(exact) == 1:
            return {"read": read, "status": "found", "candidates": exact}
    # 판매 중인 약에 같은 이름이 없으면, 허가가 취하된 약인지 본다 (오래된 약봉지)
    withdrawn = [d for d in search_withdrawn(_core(read) or read) if _key(_base(d["item_name"])) == _key(read)]
    if withdrawn:
        return {"read": read, "status": "withdrawn", "candidates": [], "withdrawn": withdrawn[0]}
    ranked = sorted(found.values(),
                    key=lambda d: -difflib.SequenceMatcher(None, _key(read), _key(_base(d["item_name"]))).ratio())
    return {"read": read, "status": "candidates" if ranked else "none", "candidates": ranked[:TOP]}


def match_names(names: list[str]) -> list[dict]:
    """이름 하나에 허가정보를 여러 번 부르므로 4개씩 함께 찾는다."""
    with ThreadPoolExecutor(max_workers=4) as pool:
        return list(pool.map(match_name, names))
