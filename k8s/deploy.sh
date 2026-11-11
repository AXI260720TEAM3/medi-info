#!/bin/bash
# 이미지를 만들어 로컬 저장소(localhost:5000)에 올리고 k8s에 적용해요
#   bash k8s/deploy.sh          만들고 배포
#   bash k8s/deploy.sh images   이미지만 만들어 올리기
# 이전 버전으로 되돌리기: kubectl -n medi-info rollout undo deploy/backend
set -euo pipefail
cd "$(dirname "$0")/.."

REGISTRY=localhost:5000
NS=medi-info

# 버전마다 다른 이름표(tag)를 붙여야 되돌리기가 돼요. 커밋 안 한 코드는 시각을 붙여요
TAG=$(git rev-parse --short HEAD)
if [ -n "$(git status --porcelain)" ]; then
  TAG=$TAG-dirty-$(date +%m%d%H%M%S)
fi
echo "버전: $TAG"

# 로컬 이미지 저장소 (automachine과 함께 써요. 이 PC에서만 열림)
if [ -z "$(docker ps -aq -f name=^registry$)" ]; then
  docker run -d --name registry --restart unless-stopped -p 127.0.0.1:5000:5000 \
    -v registry-data:/var/lib/registry registry:3.1.2
fi
docker start registry >/dev/null

# 카카오 지도 키는 빌드 인자로 (없으면 빈 값 → Leaflet 지도)
KAKAO=$(sed -n 's/^VITE_KAKAO_MAP_KEY=//p' frontend/.env.local 2>/dev/null | tr -d '\r' || true)
docker build -q -t $REGISTRY/medi-backend:$TAG backend
docker build -q -t $REGISTRY/medi-web:$TAG -f frontend/Dockerfile.prod --build-arg VITE_KAKAO_MAP_KEY="$KAKAO" frontend
docker build -q -t $REGISTRY/medi-ops:$TAG ops
for name in backend web ops; do
  docker push -q $REGISTRY/medi-$name:$TAG
done
[ "${1:-}" = images ] && exit 0

kubectl apply -f k8s/namespace.yaml

# 비밀 값은 .env에만 있고(커밋 안 함) 클러스터 안의 Secret으로 옮겨요. 파일로 남기지 않아요
# DB_HOST·DB_PORT·OLLAMA_URL은 k8s 주소가 달라서 Secret에 넣지 않고 config.yaml에 둬요
set -a; source .env; set +a
kubectl -n $NS create secret generic medi-secrets \
  --from-literal=DB_USER="$DB_USER" --from-literal=DB_PASS="$DB_PASS" --from-literal=DB_NAME="$DB_NAME" \
  --from-literal=DATA_GO_KR_KEY="$DATA_GO_KR_KEY" --from-literal=JWT_SECRET="$JWT_SECRET" \
  --from-literal=SMTP_USER="${SMTP_USER:-}" --from-literal=SMTP_PASS="${SMTP_PASS:-}" \
  --dry-run=client -o yaml | kubectl apply -f -
# 운영 API 열쇠 (백엔드 → ops). 처음 한 번만 무작위로 만들고, 화면에도 파일에도 남기지 않아요
if ! kubectl -n $NS get secret ops-token >/dev/null 2>&1; then
  kubectl -n $NS create secret generic ops-token \
    --from-literal=token="$(python3 -c 'import secrets; print(secrets.token_hex(32))')" >/dev/null
fi
# DB 초기 SQL (compose의 ./db/init)
kubectl -n $NS create configmap db-init --from-file=db/init \
  --dry-run=client -o yaml | kubectl apply -f -
# 사전 적재 Job에 넣을 스크립트와 CSV (data/dict/*.csv를 고치면 다음 배포 때 DB에 들어가요)
kubectl -n $NS create configmap dict-scripts --from-file=scripts/load_dict.py --from-file=scripts/load_synonym.py \
  --dry-run=client -o yaml | kubectl apply -f -
kubectl -n $NS create configmap dict-data --from-file=data/dict \
  --dry-run=client -o yaml | kubectl apply -f -
# Job은 한 번 끝나면 내용을 바꿀 수 없어서, 옛 것을 지우고 새로 만들어요
kubectl -n $NS delete job dict-load --ignore-not-found

# 관리자 화면은 평소 medi.localhost에서만 (Funnel 주소는 404). 다른 기기로 발표하는 날만 .env에 ADMIN_ON_FUNNEL=1
# 끝나면 ADMIN_ON_FUNNEL을 지우고 다시 배포 + tailscale funnel reset
ADMIN_HOSTS=medi.localhost
if [ "${ADMIN_ON_FUNNEL:-}" = 1 ] && [ -n "${FUNNEL_HOST:-}" ]; then
  ADMIN_HOSTS="medi.localhost,$FUNNEL_HOST"
  echo "⚠ 관리자 화면을 Funnel 주소(인터넷 공개)에서도 열어요. 발표가 끝나면 .env의 ADMIN_ON_FUNNEL을 지우고 다시 배포하세요"
fi
OLD_ADMIN_HOSTS=$(kubectl -n $NS get configmap backend-config -o jsonpath='{.data.ADMIN_HOSTS}' 2>/dev/null || true)

# DB 백업이 쌓일 폴더 (k8s/backup.yaml). 파드가 WSL 사용자(1000번)로 쓰니까 미리 만들어 둬요
mkdir -p backups

# 이미 있는 DB에 나중에 추가한 SQL(db/init/03 이후, 여러 번 실행해도 안전한 것만)을 새 백엔드보다 먼저 넣어요
# (처음 만드는 DB는 db-init이 자동으로 다 실행해요. 02_schema는 처음 한 번용이라 여기서 빼요)
if kubectl -n $NS get pod db-0 >/dev/null 2>&1; then
  kubectl -n $NS wait --for=condition=ready pod/db-0 --timeout=120s >/dev/null
  for f in db/init/0[3-9]_*.sql; do
    kubectl -n $NS exec -i db-0 -- sh -c 'psql -q -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB"' < "$f"
    echo "DB 추가 SQL: $f"
  done
fi

# 파일에는 :dev라고 적혀 있고, 배포할 때 이번 버전으로 바꿔요. 이름표가 바뀌면 k8s가 새 파드로 하나씩 갈아 끼워요
# 백업 폴더도 파일에는 BACKUP_DIR이라고만 적고, 이 PC의 실제 경로로 바꿔요 (팀원마다 홈 폴더가 달라서)
kubectl kustomize k8s | sed -e "s#\(localhost:5000/medi-[a-z]*\):dev#\1:$TAG#" -e "s#^\(  ADMIN_HOSTS:\) .*#\1 $ADMIN_HOSTS#" \
  -e "s#path: BACKUP_DIR#path: $PWD/backups#" | kubectl apply -f -
kubectl -n $NS annotate deploy backend web ops kubernetes.io/change-cause="$TAG" --overwrite
# 환경 변수는 파드가 켜질 때 한 번 읽어요. 이미지가 같아도 ADMIN_HOSTS가 바뀌었으면 backend를 다시 켜요
if [ -n "$OLD_ADMIN_HOSTS" ] && [ "$OLD_ADMIN_HOSTS" != "$ADMIN_HOSTS" ]; then
  kubectl -n $NS rollout restart deploy/backend
fi
# 사전 적재: 멈춰 둔 CronJob 설계도로 이번 배포의 Job을 만들어요 (dict-job.yaml)
kubectl -n $NS create job dict-load --from=cronjob/dict-load

# Tailscale Funnel 주소(https://○○.ts.net)로도 받기. 이 PC 전용이라 .env의 FUNNEL_HOST가 있을 때만 만들어요
# (ingress.yaml에 주소를 적으면 팀원 PC에선 쓸모없고, Tailscale 주소가 저장소에 남아요)
if [ -n "${FUNNEL_HOST:-}" ]; then
  kubectl apply -f - <<EOF
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: medi-info-funnel
  namespace: $NS
spec:
  rules:
    - host: $FUNNEL_HOST
      http:
        paths:
          - { path: /api, pathType: Prefix, backend: { service: { name: backend, port: { number: 8000 } } } }
          - { path: /,    pathType: Prefix, backend: { service: { name: web,     port: { number: 8080 } } } }
EOF
else
  kubectl -n $NS delete ingress medi-info-funnel --ignore-not-found
fi

kubectl -n $NS rollout status statefulset/db --timeout=180s
kubectl -n $NS wait --for=condition=complete job/dict-load --timeout=180s
kubectl -n $NS logs job/dict-load
for name in backend web ops; do
  kubectl -n $NS rollout status deploy/$name --timeout=180s
done
echo "열기: http://medi.localhost"
[ -n "${FUNNEL_HOST:-}" ] && echo "밖에서(Funnel을 켰을 때): https://$FUNNEL_HOST"
exit 0
