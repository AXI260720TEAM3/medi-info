import os

DB_USER = os.getenv("DB_USER")
DB_PASS = os.getenv("DB_PASS")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")

OLLAMA_URL = os.getenv("OLLAMA_URL")
# AI가 한 번에 읽는 길이(토큰). 정하지 않으면 Ollama가 2048만 읽고 프롬프트 앞부분(규칙)부터 버려요 (11/11 레녹스정)
# - 같은 모델을 부르는 곳은 모두 이 값을 써야 해요. 값이 다르면 Ollama가 부를 때마다 모델을 다시 올려 모두 느려져요
#   (11/11: 팀원 코드(값 없음)와 번갈아 불러 10분에 34번 다시 올림) → Ollama 서버의 OLLAMA_CONTEXT_LENGTH도 같은 값으로
# - 8192는 동시 처리 2개(OLLAMA_NUM_PARALLEL=2)로 나뉘어 질문 하나가 4096만 썼어요. 16384는 RTX 3060 8GB에 100% GPU로 들어가요
# - GPU가 작은 PC는 .env에 OLLAMA_NUM_CTX=8192처럼 낮추고, 그 PC의 Ollama 서버 값도 같게 맞춰요
OLLAMA_NUM_CTX = int(os.getenv("OLLAMA_NUM_CTX", "16384"))
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