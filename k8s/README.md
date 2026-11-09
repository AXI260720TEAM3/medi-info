# medi-info k8s (k3s)

개발은 지금처럼 `docker compose`로 하고, k8s는 **배포·시연용**이에요. WSL 메모리가 8GB라서 둘을 동시에 띄우지 않아요.

```
[브라우저] ─ http://medi.localhost (이 PC) ─┐
[휴대폰]  ─ https://○○.ts.net (Funnel) ────┤
                                            ▼
                              Traefik Ingress (k3s 기본)
                               ├ /api → backend (Deployment) ──┬─ db (StatefulSet + 저장 공간)
                               └ /    → web (nginx + React)    └─ ollama (k8s 밖, 이 PC의 Ollama)
                              CronJob privacy-purge: 매일 03:00 질문 기록 90일 정리
```

| 파일 | 내용 |
|---|---|
| `namespace.yaml` | `medi-info` 이름표 (같은 k3s의 automachine과 섞이지 않게) |
| `config.yaml` | 비밀이 아닌 설정 (`DB_HOST`, `OLLAMA_URL`) |
| `db.yaml` | PostgreSQL + pgvector, 처음 켤 때 `db/init`의 SQL 실행 |
| `ollama.yaml` | k8s 밖의 Ollama를 가리키는 주소록 (`10.42.0.1` = 파드에서 본 이 PC) |
| `backend.yaml` | FastAPI, 상태 검사 3종, 무중단 배포(`preStop`) |
| `web.yaml` | `frontend/Dockerfile.prod`로 만든 nginx 화면 |
| `ingress.yaml` | `medi.localhost`의 `/api`·`/` 나누기 |
| `privacy-cron.yaml` | 매일 질문 기록 정리 (PR #74) |
| `deploy.sh` | 이미지 만들기 → 로컬 저장소에 올리기 → Secret 만들기 → 적용 |
| `cluster/` | 클러스터에 **한 번만** 하는 설정 (아래) |

---

## 처음 한 번 (PC마다)

k3s가 설치돼 있어야 해요 (`curl -sfL https://get.k3s.io | sh -`). 이 PC에는 이미 있어요.

```bash
cd ~/projects/medi-info
# 1) k3s가 로컬 이미지 저장소(localhost:5000)에서 이미지를 받게
sudo cp k8s/cluster/registries.yaml /etc/rancher/k3s/registries.yaml
sudo systemctl start k3s
# 2) WSL 미러 네트워크에서 Traefik이 80번을 직접 열게 (automachine과 함께 씀. 이미 했으면 건너뛰기)
sudo kubectl apply -f k8s/cluster/traefik-config.yaml
# 3) 파드가 인터넷(공공 API)에 나갈 수 있게 + k3s 켤 때마다 자동으로
sudo bash k8s/cluster/wsl-masquerade.sh install
```

카카오 지도를 k8s에서도 쓰려면 카카오 개발자 사이트의 웹 도메인에 `http://medi.localhost`를 추가해요. 없으면 Leaflet 지도가 나와요.

## 켜기, 배포, 끄기

```bash
docker compose stop                    # 개발용 끄기 (데이터는 그대로)
sudo systemctl start k3s               # k3s 켜기 (부팅해도 자동으로 안 켜져요)
kubectl -n automachine scale deploy,statefulset --all --replicas=0   # automachine 재우기 (메모리)
bash k8s/deploy.sh                     # 만들고 배포 → http://medi.localhost
```

```bash
sudo k3s-killall.sh                    # k3s 끄기 (systemctl stop만으로는 파드가 남아요)
docker compose start                   # 개발용 다시 켜기
```

- 코드를 바꿨으면 `bash k8s/deploy.sh`만 다시 하면 돼요. 바뀐 이미지만 새로 올리고, 파드를 하나씩 갈아 끼워요(배포 중 요청 334번에서 오류 0번 확인).
- k8s의 DB는 compose DB와 **다른 저장 공간**이에요. 처음엔 빈 DB(표만 있음)라서 회원가입부터 다시 해요.
- 비밀 값은 `.env`에서 바로 클러스터의 Secret `medi-secrets`로 들어가요. 파일로 남기지 않아요.

## 휴대폰에서 https로 (Tailscale Funnel)

내 위치·Service Worker·푸시 알림은 브라우저가 `https://`(또는 `localhost`)에서만 허락해요. ZeroTier(`http://`)로는 안 돼요. Tailscale Funnel이 인증서까지 붙인 공개 주소를 만들어 줘요.

```bash
# 1) WSL: .env에 이 PC의 Tailscale 주소를 적고 배포 (deploy.sh가 그 주소용 Ingress를 하나 더 만들어요)
echo 'FUNNEL_HOST=기기이름.tailXXXX.ts.net' >> .env   # Windows에서 tailscale status --json 의 Self.DNSName (끝의 . 빼고)
bash k8s/deploy.sh
```

```powershell
# 2) Windows PowerShell: 인터넷에 공개 (휴대폰에 Tailscale이 없어도 돼요)
tailscale funnel --bg 80        # https://○○.ts.net → 이 PC의 80번(Traefik)
tailscale funnel status
tailscale funnel reset          # 끄기 (주소를 아는 누구나 들어올 수 있어서, 시험·시연이 끝나면 꼭)
```

- 확인은 **휴대폰(와이파이·Tailscale 끄고 LTE)**으로 해요. 이 PC에서 `https://○○.ts.net`을 열면 인증서 경고가 나와요: 이 PC 안에서는 그 주소가 Tailscale 내부 주소로 바뀌고, 443번은 Traefik(`traefik-config.yaml`의 hostNetwork)이 잡고 있어서 Traefik의 가짜 인증서(`TRAEFIK DEFAULT CERT`)가 대답해요. 밖에서 오는 Funnel 요청은 Tailscale 안으로 들어와 80번으로 넘겨져서 괜찮아요.
- 카카오 지도를 쓰려면 카카오 개발자 사이트의 웹 도메인에 `https://○○.ts.net`도 추가해요.

## 버전과 되돌리기

배포할 때마다 이미지에 `커밋번호`(커밋 안 했으면 `커밋번호-dirty-시각`) 이름표가 붙어요.

```bash
kubectl -n medi-info rollout history deploy/backend      # 배포 기록 (CHANGE-CAUSE = 버전)
kubectl -n medi-info rollout undo deploy/backend         # 바로 전 버전으로
kubectl -n medi-info rollout undo deploy/backend --to-revision=3   # 특정 번호로
```

- 되돌리면 옛 번호로 가지 않고 **새 번호**가 붙어요 (4번 버전으로 되돌리면 4가 사라지고 6이 생김). 기록이 거꾸로 가지 않게요.
- 옛 이미지를 그대로 다시 써서 몇 초면 끝나요. 이미지 이름표가 버전마다 달라서 가능해요.
- `undo`는 **비상 버튼**이에요. 클러스터만 옛 버전이 되고 `k8s/*.yaml`·코드는 그대로라, 다음 `deploy.sh`는 다시 최신을 올려요 (`was previously managed with 'kubectl apply'` 경고가 이 뜻). 오래 옛 버전으로 두려면 git에서 코드를 되돌리고 `deploy.sh`로 배포해요.

## 확인

```bash
kubectl -n medi-info get pods                            # 모두 Running, READY 1/1
curl -H 'Host: medi.localhost' http://127.0.0.1/api/health   # DB 표 수, Ollama 모델
kubectl -n medi-info logs deploy/backend --tail=30       # 백엔드 기록
kubectl -n medi-info top pods                            # 메모리·CPU
kubectl -n medi-info create job --from=cronjob/privacy-purge purge-now   # 질문 기록 정리를 지금 한 번
kubectl -n medi-info logs job/purge-now
```

## 상태 검사 (probe)

| 검사 | 주소 | 실패하면 |
|---|---|---|
| startup | `/api/health/live` | 최대 60초 기다려요 (서버가 켜지는 중) |
| liveness | `/api/health/live` (아무것도 안 봄) | 30초 응답이 없으면 파드를 **다시 켜요** |
| readiness | `/api/health/ready` (DB만) | 다시 켜지 않고 **요청만 안 보내요**. DB가 돌아오면 저절로 다시 받아요 |

Ollama는 검사하지 않아요. AI가 꺼져도 검색·약국·내 약은 돼야 하니까요 (REQ-N-012). DB를 꺼 보면 backend가 `READY 0/1`, `RESTARTS 0`이 되고, DB를 켜면 돌아와요.

## 막혔을 때

| 증상 | 원인과 해결 |
|---|---|
| 약 검색·약국이 "서버가 응답하지 않아요" | 파드가 인터넷에 못 나감. `sudo bash k8s/cluster/wsl-masquerade.sh` (WSL 미러 네트워크가 flannel의 무작위 포트 답장을 버려요) |
| `http://medi.localhost`가 안 열림 | `kubectl -n kube-system get pods`에서 traefik이 Running인지, `traefik-config.yaml`을 적용했는지 |
| 배포했는데 `ImagePullBackOff` | `docker start registry`, `registries.yaml`을 넣고 k3s를 다시 켰는지 |
| 메모리가 모자람 (파드가 `Pending`·`OOMKilled`) | compose와 automachine을 껐는지. `free -h` |
| 화면 새로고침하면 404 | `frontend/nginx.conf`의 `try_files ... /index.html` |
| Funnel 주소가 "no available server" | `.env`에 `FUNNEL_HOST`를 넣고 `deploy.sh`를 했는지 (없으면 automachine의 `/` 규칙으로 가요) |
| Funnel 주소가 "사이트에 연결할 수 없음" | `tailscale funnel status`가 `No serve config`이면 `tailscale funnel --bg 80` |
