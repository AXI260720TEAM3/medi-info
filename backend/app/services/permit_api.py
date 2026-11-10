import html
import re
from collections import Counter
import xml.etree.ElementTree as ET

import httpx
from ..config import DATA_GO_KR_KEY
from .api_cache import ttl_cache

URL = "https://apis.data.go.kr/1471000/DrugPrdtPrmsnInfoService08/getDrugPrdtPrmsnInq08"
DETAIL_URL = "https://apis.data.go.kr/1471000/DrugPrdtPrmsnInfoService08/getDrugPrdtPrmsnDtlInq08"

# 허가정보 칸 이름(대문자) -> 우리 이름
FIELDS = {
    "ITEM_SEQ": "item_seq",
    "ITEM_NAME": "item_name",
    "ENTP_NAME": "entp_name",
    "SPCLTY_PBLC": "etc_otc",
}

TIMEOUT = 8   # 한 번에 8초까지, 연결·시간 초과면 한 번 더 (drug_api와 같은 규칙)


def _get(url, params):
    """허가정보 API 부르기. 느리거나 끊기면 한 번만 더 해 봐요"""
    for attempt in (1, 2):
        try:
            return httpx.get(url, params=params, timeout=TIMEOUT)
        except (httpx.TimeoutException, httpx.ConnectError):
            if attempt == 2:
                raise


def _rename(item):
    return {ours: item.get(api) for api, ours in FIELDS.items()}

@ttl_cache(3600)
def search_permit(name):
    params = {"serviceKey": DATA_GO_KR_KEY, "type":"json", "item_name":name, "numOfRows":100}
    res = _get(URL, params)
    res.raise_for_status()
    items = res.json()["body"].get("items") or []

    result = []
    # 취소된 약, 수출용 약은 뺀다
    for item in items:
        if item.get("CANCEL_NAME") == "정상" and "(수출용)" not in item.get("ITEM_NAME",""):
            result.append(_rename(item))
    return result


def search_withdrawn(name):
    """허가가 취소·취하된 약만 찾는다. 약봉지가 오래되면 지금은 팔지 않는 약이 나올 수 있다."""
    params = {"serviceKey": DATA_GO_KR_KEY, "type": "json", "item_name": name, "numOfRows": 100}
    res = _get(URL, params)
    res.raise_for_status()
    result = []
    for item in res.json()["body"].get("items") or []:
        if item.get("CANCEL_NAME") not in (None, "", "정상"):
            date = item.get("CANCEL_DATE") or ""
            result.append({
                **_rename(item),
                "cancel_name": item["CANCEL_NAME"],  # 취하, 취소 등
                "cancel_date": f"{date[:4]}-{date[4:6]}-{date[6:8]}" if len(date) == 8 else date,
            })
    return result


# 허가정보 목록 API는 성분을 영어 이름(item_ingr_name)으로만 찾아요. 약 이름 괄호에서 못 찾는 성분만 여기에
INGREDIENT_EN = {
    "덱스트로메토르판": "Dextromethorphan Hydrobromide",
    "클로르페니라민": "Chlorpheniramine Maleate",
    "슈도에페드린": "Pseudoephedrine Hydrochloride",
    "카페인": "Caffeine",
}


@ttl_cache(3600)
def english_ingredient(korean):
    """한글 성분 이름 → 허가정보의 영어 성분 이름. 못 찾으면 None
    약 이름에 '(아세트아미노펜)'처럼 성분이 괄호로 붙은 단일 성분 약들을 모아, 가장 많이 쓰인 영어 이름을 골라요"""
    if korean in INGREDIENT_EN:
        return INGREDIENT_EN[korean]
    params = {"serviceKey": DATA_GO_KR_KEY, "type": "json", "item_name": korean, "numOfRows": 100}
    res = _get(URL, params)
    res.raise_for_status()
    items = res.json()["body"].get("items") or []
    names = Counter(
        item["ITEM_INGR_NAME"] for item in items
        if f"({korean})" in item.get("ITEM_NAME", "") and str(item.get("ITEM_INGR_CNT")) == "1" and item.get("ITEM_INGR_NAME")
    )
    return names.most_common(1)[0][0] if names else None


@ttl_cache(3600)
def search_permit_by(field, value):
    """허가정보를 성분(item_ingr_name, 영어)이나 회사(entp_name)로 찾기. (허가정보 전체 건수, 앞 100건 중 정상 약)
    한 번에 100건까지만 받아요. 아세트아미노펜처럼 1,000건이 넘는 성분은 전부 받으면 열 번 넘게 불러야 해서 느려요"""
    params = {"serviceKey": DATA_GO_KR_KEY, "type": "json", field: value, "numOfRows": 100}
    res = _get(URL, params)
    res.raise_for_status()
    body = res.json()["body"]
    items = body.get("items") or []
    return body.get("totalCount") or 0, [_rename(item) for item in items
            if item.get("CANCEL_NAME") == "정상" and "(수출용)" not in item.get("ITEM_NAME", "")]


def _clean(text):
    """문단 글에 섞인 HTML(표, &gt; 같은 기호)을 읽을 수 있는 글로. 표는 한 줄에 칸을 ' | '로."""
    text = text.replace("\n", " ")             # 원본 코드의 줄바꿈은 무시
    text = re.sub(r"</tr>", "\n", text)        # 표의 한 줄이 끝나면 줄바꿈
    text = re.sub(r"</td>", " | ", text)       # 칸이 끝나면 구분선
    text = re.sub(r"<[^>]+>", " ", text)       # 나머지 태그는 지움
    text = html.unescape(text)                 # &gt; → >
    lines = [" ".join(line.split()).strip(" |") for line in text.split("\n")]
    return "\n".join(line for line in lines if line)


def doc_to_text(xml):
    """허가정보 문서(XML)를 줄글로 바꾼다. 문서가 없으면 None."""
    if not xml:
        return None
    root = ET.fromstring(xml)
    lines = []
    for article in root.iter("ARTICLE"):
        if article.get("title"):
            lines.append(article.get("title"))
        for p in article.iter("PARAGRAPH"):
            if p.text:
                lines.append(_clean(p.text))
    return "\n".join(lines)


@ttl_cache(3600)
def get_permit_detail(item_seq):
    """품목번호로 허가정보 상세를 받아 e약은요와 같은 칸 이름으로 돌려준다. 없으면 None."""
    params = {"serviceKey": DATA_GO_KR_KEY, "type": "json", "item_seq": item_seq}
    res = _get(DETAIL_URL, params)
    res.raise_for_status()
    items = res.json()["body"].get("items") or []
    if not items:
        return None
    item = items[0]

    return {
        "item_seq": item["ITEM_SEQ"],
        "item_name": item["ITEM_NAME"],
        "entp_name": item["ENTP_NAME"],
        "etc_otc": item["ETC_OTC_CODE"],
        "efcy": doc_to_text(item["EE_DOC_DATA"]),
        "use_method": doc_to_text(item["UD_DOC_DATA"]),
        "atpn": doc_to_text(item["NB_DOC_DATA"]),
        "deposit": item["STORAGE_METHOD"],
        "has_easy": False,
    }

