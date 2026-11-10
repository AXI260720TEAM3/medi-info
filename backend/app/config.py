import os

DB_USER = os.getenv("DB_USER")
DB_PASS = os.getenv("DB_PASS")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")

OLLAMA_URL = os.getenv("OLLAMA_URL")
OPS_URL = os.getenv("OPS_URL")            # 운영 API (k8s에서만). 없으면 운영 탭은 503
OPS_TOKEN = os.getenv("OPS_TOKEN", "")
# 관리자 API를 받는 주소 목록 (쉼표로). 비어 있으면 어느 주소든 받아요 (compose 개발)
ADMIN_HOSTS = [h.strip() for h in os.getenv("ADMIN_HOSTS", "").split(",") if h.strip()]
DATA_GO_KR_KEY = os.getenv("DATA_GO_KR_KEY")
JWT_SECRET = os.getenv("JWT_SECRET")

SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASS = os.getenv("SMTP_PASS", "")