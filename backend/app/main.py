from fastapi import FastAPI
from .routes import health, drugs, chat, together, auth, my_meds, pharmacy

app = FastAPI(title="일반의약품 정보 찾기 API")

app.include_router(health.router)
app.include_router(drugs.router)
app.include_router(chat.router)
app.include_router(together.router)
app.include_router(auth.router)
app.include_router(my_meds.router)
app.include_router(pharmacy.router)
