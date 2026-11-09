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
for name in backend web; do
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

# 파일에는 :dev라고 적혀 있고, 배포할 때 이번 버전으로 바꿔요. 이름표가 바뀌면 k8s가 새 파드로 하나씩 갈아 끼워요
kubectl kustomize k8s | sed "s#\(localhost:5000/medi-[a-z]*\):dev#\1:$TAG#" | kubectl apply -f -
kubectl -n $NS annotate deploy backend web kubernetes.io/change-cause="$TAG" --overwrite

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
for name in backend web; do
  kubectl -n $NS rollout status deploy/$name --timeout=180s
done
echo "열기: http://medi.localhost"
[ -n "${FUNNEL_HOST:-}" ] && echo "밖에서(Funnel을 켰을 때): https://$FUNNEL_HOST"
exit 0
