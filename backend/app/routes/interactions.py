"""로그인 없이 쓰는 함께 먹기 판정 (E안 6번, API 계약 3장): POST /api/interactions/check

AI 질문의 [함께 먹어도 되는지 확인] 버튼과 🔴 자동 알림이 불러요.
- 판정은 내 약 점검(/api/my-meds/check)과 같은 함수 check_interaction (식약처 DUR 병용금기·성분 겹침·같은 계열)
- 응답 모양도 /api/my-meds/check와 같아서, 화면은 같은 결과 카드로 그려요
- 약 목록은 요청으로 받고, 저장하지 않고 질문 기록에도 남기지 않아요 (AI를 부르지 않아요)
"""
import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from ..deps import get_optional_user
from ..services.dur_api import check_interaction
from ..services.my_meds import get_profile

router = APIRouter(prefix="/api/interactions", tags=["Interactions"])

API_DOWN = "약 정보 서버가 응답하지 않아요. 잠시 후 다시 시도해 주세요."
MIN_DRUGS, MAX_DRUGS = 2, 10   # AI 질문의 "이 대화의 약"도 10개까지


class CheckDrug(BaseModel):
    item_seq: str = Field(min_length=1, max_length=20)
    item_name: str = Field(default="", max_length=200)


class CheckRequest(BaseModel):
    # 같은 약이 섞여 와도 받을 수 있게 넉넉히 받고, 겹친 것을 뺀 뒤 2~10개인지 봐요
    drugs: list[CheckDrug] = Field(max_length=MAX_DRUGS * 2)


@router.post("/check")
def check(data: CheckRequest, user: dict | None = Depends(get_optional_user)):
    # 품목번호 → 이름 (같은 약은 한 번만, 처음 온 이름을 써요)
    names = {}
    for drug in data.drugs:
        names.setdefault(drug.item_seq, drug.item_name or drug.item_seq)
    if not MIN_DRUGS <= len(names) <= MAX_DRUGS:
        raise HTTPException(status_code=422, detail=f"약을 {MIN_DRUGS}개에서 {MAX_DRUGS}개까지 담아 주세요.")

    # 내 약 점검과 같은 규칙: 프로필이 소아면 성인 최대 용량 문장을 빼요 (로그인 + 건강정보 동의한 사람만 프로필이 있어요)
    profile = get_profile(user["user_id"]) if user and user["agree_health"] else None
    try:
        results = check_interaction(list(names), show_max_dose=profile != "소아")
    except httpx.HTTPError:
        raise HTTPException(status_code=503, detail=API_DOWN)

    for result in results:
        result["item_name_a"] = names[result["item_seq_a"]]
        result["item_name_b"] = names[result["item_seq_b"]]
    return {"level": results[0]["level"] if results else None, "results": results}
