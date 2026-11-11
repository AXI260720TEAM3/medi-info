# medi-info k8s (k3s)

개발은 지금처럼 `docker compose`로 하고, k8s는 **배포·시연용**이에요. WSL 메모리가 8GB라서 둘을 동시에 띄우지 않아요.

```
[브라우저] ─ http://medi.localhost (이 PC) ─┐
[휴대폰]  ─ https://○○.ts.net (Funnel) ────┤
                                            ▼
                              Traefik Ingress (k3s 기본)
                               ├ /api → backend (Deployment) ──┬─ db (StatefulSet + 저장 공간)
                               │                               ├─ ollama (k8s 밖, 이 PC의 Ollama)
                               │                               └─ ops (운영 API, k8s 권한은 이 파드만)
                               └ /    → web (nginx + React)
                              CronJob privacy-purge: 매일 03:00 질문 기록 90일 정리
                              CronJob dict-load: 멈춰 둔 설계도 (배포·운영 탭에서 Job으로 복사해 사전 적재)
                              CronJob db-backup: 매일 12:40 DB 복사본 → 이 PC의 backups/ (최근 3개)
```

| 파일 | 내용 |
|---|---|
| `namespace.yaml` | `medi-info` 이름표 (같은 k3s의 automachine과 섞이지 않게) |
| `config.yaml` | 비밀이 아닌 설정 (`DB_HOST`, `OLLAMA_URL`, `OLLAMA_NUM_CTX`, `OPS_URL`, `ADMIN_HOSTS`) |
| `db.yaml` | PostgreSQL + pgvector, 처음 켤 때 `db/init`의 SQL 실행 |
| `ollama.yaml` | k8s 밖의 Ollama를 가리키는 주소록 (`10.42.0.1` = 파드에서 본 이 PC) |
| `backend.yaml` | FastAPI, 상태 검사 3종, 무중단 배포(`preStop`) |
| `web.yaml` | `frontend/Dockerfile.prod`로 만든 nginx 화면 |
| `ingress.yaml` | `medi.localhost`의 `/api`·`/` 나누기 |
| `privacy-cron.yaml` | 매일 질문 기록 정리 (PR #74) |
| `backup.yaml` | 매일 DB 백업 → `backups/` (커밋 안 함, 최근 3개). 폴더 경로는 `deploy.sh`가 채워요 |
| `ops.yaml` | 운영 API (관리자 화면 운영 탭). 전용 계정·권한(RBAC), 백엔드만 들어오게(NetworkPolicy) |
| `dict-job.yaml` | 배포할 때마다 사전 적재 (`data/dict/*.csv` → 위험 증상·주의 대상·고정 문구·동의어). 이게 없으면 AI 답이 500 (고정 문구가 없어서) |
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

- 진짜 확인은 **휴대폰(와이파이·Tailscale 끄고 LTE)**으로 해요. 이 PC에서도 열려요.
- Traefik은 PC의 443번을 잡지 않아요(`traefik-config.yaml`의 `websecure`를 8444번으로 옮김). 443번을 Traefik이 잡고 있으면, 이 PC에서 `https://○○.ts.net`을 열 때 Tailscale 대신 Traefik이 가짜 인증서(`TRAEFIK DEFAULT CERT`)로 대답해서 인증서 경고가 났어요 (11/09에 고침)
- 카카오 지도를 쓰려면 카카오 개발자 사이트의 웹 도메인에 `https://○○.ts.net`도 추가해요.
- 관리자 화면은 Funnel 주소에서 **404**예요(아래 운영 탭 절). 다른 기기(강의실 PC)로 발표하는 날만 이렇게 열어요:

  ```bash
  # 발표 전: 관리자 비밀번호를 길고 무작위로 바꾸기 (계정 찾기 → 비밀번호 재설정)
  echo 'ADMIN_ON_FUNNEL=1' >> .env && bash k8s/deploy.sh     # ⚠ 경고가 나오면 열린 것
  # 발표 뒤: 꼭 닫기
  sed -i '/^ADMIN_ON_FUNNEL=/d' .env && bash k8s/deploy.sh   # Funnel 주소의 관리자 API가 다시 404
  tailscale funnel reset                                      # (Windows PowerShell) 공개 주소 끄기
  ```

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

## 관리자 화면 운영 탭 (ops)

`http://medi.localhost/admin` → 운영 탭에서 kubectl 없이 할 수 있는 일:

| 할 일 | 하는 일 |
|---|---|
| 상태 보기 | 워크로드별 준비 수·**버전(커밋번호)**, 파드 상태·재시작 횟수·**지난번 종료 이유**(메모리 한도 초과 등), 최근 사전 적재 3번, CronJob 마지막 실행 |
| 자원 사용량 | 노드(이 PC의 WSL 전체, Ollama 포함)와 파드별 CPU·메모리를 한도 대비 막대로. metrics-server 값이라 15초마다 새로 봐요 |
| 다시 시작 | `backend`·`web`만 (`kubectl rollout restart`와 같음, 하나씩 갈아 끼워서 끊기지 않아요). db·ops는 안 돼요 |
| 사전 다시 적재 | 멈춰 둔 `dict-load` CronJob을 복사해 Job을 만들어요. CSV는 **마지막 배포 때** 넣은 것이라, 새 CSV는 머지 뒤 `deploy.sh` |
| 백업과 저장 공간 | 백업 파일 목록, 마지막 백업 작업 결과, **지금 백업** 버튼, DB 크기 / 저장 공간(5Gi), 큰 표 5개. 36시간 넘게 새 백업이 없으면 "오래됨" |

```
[관리자 브라우저] → backend /api/admin/ops/* (관리자 로그인 확인) → ops:8000 (OPS_TOKEN 확인) → k8s API
```

- **k8s 권한은 ops 파드만** 가져요. 손님을 받는 backend는 권한이 없어서, backend가 뚫려도 k8s를 직접 만질 수 없어요. ops 권한에도 Secret 읽기·exec·지우기는 없어요.
- 노드는 이름공간 밖이라 `ClusterRole medi-info-ops-nodes`로 **노드 정보·사용량 읽기만** 따로 줘요.
- 대시보드 "서버 상태"는 `/api/admin/health`로 통계와 따로 확인해요: DB 응답, Ollama 응답·모델이 GPU에 올라갔는지·문맥 길이가 `OLLAMA_NUM_CTX`와 같은지, 사전(고정 문구·위험 증상이 비었는지). 관리자 확인에도 DB를 써서, DB가 멈추면 "확인 실패"로 보여요.
- ops에는 **backend 파드만** 들어올 수 있어요(NetworkPolicy). 같은 클러스터의 automachine 등은 막혀요.
- `OPS_TOKEN`은 `deploy.sh`가 처음 한 번 무작위로 만들어 Secret `ops-token`에 넣어요(파일로 안 남김).
- 관리자 API는 `ADMIN_HOSTS`(medi.localhost)로 온 요청만 받아요. **Funnel 주소로는 404**라 바깥에서는 관리자 화면이 없는 것처럼 보여요.
- compose에는 ops가 없어서 운영 탭은 k8s에서만 돼요.

## DB에 나중에 더한 SQL

`db/init/02_schema.sql`은 DB를 처음 만들 때 한 번만 돌아요. 그 뒤에 더한 `03_`·`04_`… 파일은 **여러 번 실행해도 안전하게**(`IF NOT EXISTS`) 쓰고,
`deploy.sh`가 배포할 때마다 이미 있는 DB에 새 백엔드보다 먼저 넣어요. compose나 팀원 PC의 DB는 그 파일을 한 번 직접 실행하면 돼요.

| 파일 | 내용 |
|---|---|
| `03_email_code.sql` | 이메일 인증번호 표 |
| `04_answer_check.sql` | 질문 기록에 AI 답변 검증 결과·막힌 초안 칸 (관리자 대시보드 "AI 답변 검증") |

## DB 백업과 되살리기

`db-backup` CronJob이 매일 12:40(한국 시간)에 `backups/db_날짜_시각.dump`를 만들고 최근 3개만 남겨요.
PC나 k3s가 꺼져 있어 놓쳐도 6시간 안에 켜면 그때 해요. 결과는 운영 탭 "백업과 저장 공간"에서 봐요.

- 다 만든 뒤 `pg_restore --list`로 한 번 읽어 보고 나서야 `.dump` 이름을 붙여요. 중간에 끊긴 파일은 남지 않아요.
- `backups/`에는 계정(비밀번호는 해시)·내 약·질문 기록이 들어 있어요. `.gitignore`에 있고, **다른 곳에 옮기거나 공유하지 마세요.**
- 질문 기록은 90일이 지나면 지우지만(privacy-purge), 지운 기록도 최근 백업 3개(최대 3일)에는 남아 있다가 사라져요.

```bash
# 지금 바로 한 번 (운영 탭의 [지금 백업]과 같아요)
kubectl -n medi-info create job --from=cronjob/db-backup backup-now

# 되살리기 전에 먼저 시험: 임시 DB에 넣어 보고 지우기 (운영 DB는 그대로)
kubectl -n medi-info exec -i db-0 -- sh -c 'createdb -U "$POSTGRES_USER" restore_test && pg_restore -U "$POSTGRES_USER" -d restore_test --no-owner' < backups/파일이름.dump
kubectl -n medi-info exec db-0 -- sh -c 'dropdb -U "$POSTGRES_USER" restore_test'

# 운영 DB를 백업으로 덮어쓰기 (그 뒤에 생긴 데이터는 사라져요). backend를 잠시 꺼서 쓰는 중인 연결이 없게 해요
kubectl -n medi-info scale deploy/backend --replicas=0
kubectl -n medi-info exec -i db-0 -- sh -c 'pg_restore --clean --if-exists --no-owner -U "$POSTGRES_USER" -d "$POSTGRES_DB"' < backups/파일이름.dump
kubectl -n medi-info scale deploy/backend --replicas=1
```

11/11 시험: 백업 70KB·몇 초, 임시 DB에 되살려 표 13개 행 수 일치, 4번 만들어 3개만 남는 것 확인. 덮어쓰기(마지막 명령)는 시험하지 않았어요.

## Ollama 문맥 길이 (`OLLAMA_NUM_CTX` = `OLLAMA_CONTEXT_LENGTH`)

Ollama는 k8s 밖(WSL의 systemd 서비스)에서 돌아요. 백엔드가 보내는 `num_ctx`와 Ollama 서버의 기본 문맥 길이가 **같아야** 해요.

- 값이 다르면 요청마다 모델을 다시 올려서 한 번에 30초씩 걸려요. 11/11에 10분 동안 34번이나 다시 올렸어요(팀원 코드는 값을 안 보내서 서버 기본값을 썼음).
- 지금 값은 **16384**예요. `OLLAMA_NUM_PARALLEL=2`라 8192로 두면 질문 하나가 4096만 쓰고 공식 자료 뒷부분(규칙·복용방법)이 잘렸어요. 16384는 RTX 3060 8GB에 100% GPU로 들어가요.
- k8s 백엔드는 `config.yaml`의 `OLLAMA_NUM_CTX`를 써요. **`.env` 값은 k8s에 안 들어와요**(`deploy.sh`는 비밀 값만 Secret에 넣음).

```bash
# 이 PC의 Ollama 서버 값 보기·바꾸기
systemctl cat ollama | grep CONTEXT_LENGTH     # Environment="OLLAMA_CONTEXT_LENGTH=16384"
sudo systemctl edit ollama                     # [Service] 아래 Environment="OLLAMA_CONTEXT_LENGTH=16384"
sudo systemctl restart ollama
ollama ps                                      # CONTEXT 16384, PROCESSOR 100% GPU 인지
```

- 값을 바꾸면 세 곳을 같이 바꿔요: Ollama 서버(`OLLAMA_CONTEXT_LENGTH`), `k8s/config.yaml`, 기본값(`backend/app/config.py`).
- GPU가 작은 팀원 PC(compose)는 `.env`에 `OLLAMA_NUM_CTX=8192`, 그 PC의 Ollama에도 `OLLAMA_CONTEXT_LENGTH=8192`.

### Ollama 프롬프트 캐시 한도 (`LLAMA_ARG_CACHE_RAM=512`)

Ollama 안의 llama-server는 지난 질문의 계산 결과를 **WSL 메모리**에 쌓아 두는 프롬프트 캐시가 있어요. 기본 한도가 **8GB**라,
약바로처럼 공식 자료가 들어간 긴 프롬프트가 계속 바뀌면 끝까지 차요(`OLLAMA_KEEP_ALIVE=-1`이라 모델이 안 내려가서 계속 쌓임).

- 11/11: 모델은 100% GPU인데 러너가 WSL 메모리 4.7GB + 스왑 3.6GB를 잡아서, WSL 남은 메모리가 0.5GB → k3s API 멈춤·파드 재시작·배포 중단.
- 한도를 512MB로: 질문 40번 뒤에도 러너 약 0.7GB, 답 시간 평균 6초로 그대로.
- Ollama 설정(`OLLAMA_*`)에는 이 항목이 없어서, llama-server가 직접 읽는 환경 변수로 줘요. automachine도 같은 Ollama라 같이 좋아져요.

```bash
sudo bash -c 'f=/etc/systemd/system/ollama.service.d/override.conf; sed -i "/LLAMA_ARG_CACHE_RAM/d" $f; echo "Environment=\"LLAMA_ARG_CACHE_RAM=512\"" >> $f; systemctl daemon-reload; systemctl restart ollama'
journalctl -u ollama --since -10min | grep "prompt cache"   # size limit: 512 MiB 인지
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
| AI 질문이 한참 걸린 뒤 500 (`NoResultFound`) | 사전이 비어 있음. `kubectl -n medi-info logs job/dict-load`로 적재 결과 확인, 없으면 `bash k8s/deploy.sh` |
| 모든 주소가 응답 없음(시간 초과), traefik이 `CrashLoopBackOff` | 와이파이 주소가 바뀜 (k3s는 켤 때 주소를 한 번 읽어요). `kubectl get node -o wide`의 INTERNAL-IP가 `ip -4 addr`의 지금 주소와 다르면 `sudo systemctl restart k3s` |
| 약 검색·약국이 "서버가 응답하지 않아요" | 파드가 인터넷에 못 나감. `sudo bash k8s/cluster/wsl-masquerade.sh` (WSL 미러 네트워크가 flannel의 무작위 포트 답장을 버려요) |
| `http://medi.localhost`가 안 열림 | `kubectl -n kube-system get pods`에서 traefik이 Running인지, `traefik-config.yaml`을 적용했는지 |
| 배포했는데 `ImagePullBackOff` | `docker start registry`, `registries.yaml`을 넣고 k3s를 다시 켰는지 |
| 메모리가 모자람 (파드가 `Pending`·`OOMKilled`) | compose와 automachine을 껐는지. `free -h` |
| AI 답이 매번 30초 넘게 걸림 | `ollama ps`의 CONTEXT가 16384가 아니거나 모델이 자꾸 다시 올라옴. 위 "Ollama 문맥 길이"대로 값 맞추기 |
| 운영 탭이 "운영 API에 연결하지 못했어요" | `kubectl -n medi-info get pods`에서 ops가 Running인지, `kubectl -n medi-info logs deploy/ops` |
| 화면 새로고침하면 404 | `frontend/nginx.conf`의 `try_files ... /index.html` |
| Funnel 주소가 "no available server" | `.env`에 `FUNNEL_HOST`를 넣고 `deploy.sh`를 했는지 (없으면 automachine의 `/` 규칙으로 가요) |
| Funnel 주소가 "사이트에 연결할 수 없음" | `tailscale funnel status`가 `No serve config`이면 `tailscale funnel --bg 80` |
