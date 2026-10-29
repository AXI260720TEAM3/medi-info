import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from ..config import OLLAMA_URL
from ..services.drug_api import search_by_name, get_by_seq

router = APIRouter(
    prefix="/api",
    tags=["Chat"]
)

class AskRequest(BaseModel):
    question: str
    drug_name:str | None = None
    item_seq:str | None = None
    
@router.post("/ask")
def ask(data:AskRequest):
    user_question = data.question
    
    if data.item_seq:
        try:
            drug = get_by_seq(data.item_seq)
        except httpx.HTTPError:
            raise HTTPException(
                status_code=503,
                detail="약 정보 서버가 응답하지 않아요."
            )

        if drug is None:
            raise HTTPException(
                status_code=404,
                detail="해당 약을 찾을 수 없어요."
            )

        
        if "보관" not in user_question:
            return {"answer": "현재는 보관방법 질문만 시험할 수 있어요."}

        storage = drug.get("deposit")

        if not storage:
            return {"answer": "공식 자료에 보관방법 정보가 없어요."}

        return {
            "answer": storage,
            "item_seq": drug["item_seq"],
            "item_name": drug["item_name"],
            "source": "식품의약품안전처 e약은요"
        }

    if data.drug_name:
        total, items = search_by_name(data.drug_name)
        return {
            "answer": "검색된 약 중 정확한 제품을 확인해 주세요.",
            "total": total,
            "items": items
        }
    
    res = httpx.post(
        f"{OLLAMA_URL}/api/generate",
        json={
            "model": "qwen2.5:7b-instruct-q4_K_M",
            "prompt": user_question,
            "stream": False
        },
        timeout=120
    )
    
    res.raise_for_status()
    answer = res.json()["response"]
    return {"answer": answer}
