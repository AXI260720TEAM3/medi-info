import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from .routes import health, drugs, chat, together, auth, my_meds, pharmacy, admin, interactions
from .services.privacy import purge_old_chat_logs


@asynccontextmanager
async def lifespan(app):
    # 서버가 켜질 때 보관 기간이 지난 질문 기록을 한 번 지워요 (매일 지우기는 k8s CronJob에서)
    try:
        logging.info("오래된 질문 기록 %d줄 삭제", purge_old_chat_logs())
    except Exception:
        logging.exception("질문 기록 정리 실패 (서버는 계속 켜요)")
    yield


app = FastAPI(title="일반의약품 정보 찾기 API", lifespan=lifespan)

app.include_router(health.router)
app.include_router(drugs.router)
app.include_router(chat.router)
app.include_router(together.router)
app.include_router(auth.router)
app.include_router(my_meds.router)
app.include_router(pharmacy.router)
app.include_router(admin.router)
app.include_router(interactions.router)
