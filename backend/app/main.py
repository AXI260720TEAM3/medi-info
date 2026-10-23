from fastapi import FastAPI
from .routes import health

app = FastAPI(title="일반의약품 정보 찾기 API")

app.include_router(health.router)