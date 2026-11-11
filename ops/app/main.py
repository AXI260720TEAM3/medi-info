"""medi-info 운영 API (기능명세 H-5). 관리자 화면의 운영 탭이 백엔드를 거쳐 불러요
- 바깥에서 바로 오는 길(Ingress)이 없어요. 같은 클러스터의 백엔드 파드만 들어올 수 있어요 (NetworkPolicy)
- 백엔드는 관리자 확인을 한 뒤 X-Ops-Token을 붙여서 불러요. 토큰이 없거나 틀리면 401
- 할 수 있는 일: 상태 보기, 자원 사용량 보기, backend·web 다시 시작, 사전 다시 적재(dict-load Job), 백업 보기·지금 백업(db-backup Job)"""
import os
import secrets
from datetime import datetime, timezone
from pathlib import Path

import httpx
from fastapi import Depends, FastAPI, Header, HTTPException

from . import k8s

OPS_TOKEN = os.environ["OPS_TOKEN"]   # 없으면 켜지지 않아요 (토큰 없이 열린 운영 API는 위험해서)
RESTARTABLE = ("backend", "web")      # Role도 이 두 이름만 patch를 허락해요
BACKUP_PATH = os.environ.get("BACKUP_PATH", "/backups")   # k8s/ops.yaml이 읽기 전용으로 붙여요
MIB = 1024 * 1024


def check_token(x_ops_token: str = Header(default="")):
    # compare_digest: 글자를 앞에서부터 비교하다 멈추지 않아서, 걸린 시간으로 토큰을 짐작할 수 없어요
    if not secrets.compare_digest(x_ops_token, OPS_TOKEN):
        raise HTTPException(status_code=401, detail="운영 토큰이 맞지 않아요.")


app = FastAPI(title="medi-info 운영 API")


@app.get("/live")
def live():
    return {"ok": True}


def _tag(image):
    return image.rsplit(":", 1)[-1]


def _workloads():
    items = k8s.get(k8s.ns("deployments", "/apis/apps/v1"))["items"] + k8s.get(k8s.ns("statefulsets", "/apis/apps/v1"))["items"]
    return [{
        "name": w["metadata"]["name"],
        "kind": w["kind"] if "kind" in w else ("StatefulSet" if "serviceName" in w["spec"] else "Deployment"),
        "want": w["spec"].get("replicas", 1),
        "ready": w["status"].get("readyReplicas", 0),
        "version": _tag(w["spec"]["template"]["spec"]["containers"][0]["image"]),
        "restartable": w["metadata"]["name"] in RESTARTABLE,
    } for w in items]


def _pods():
    pods = []
    for p in k8s.get(k8s.ns("pods"))["items"]:
        statuses = p["status"].get("containerStatuses") or []
        # 지난번에 꺼진 이유 (OOMKilled = 메모리 한도를 넘어 k8s가 끔, Error = 프로그램이 오류로 끝남)
        last = next((s["lastState"]["terminated"] for s in statuses if s.get("lastState", {}).get("terminated")), None)
        pods.append({
            "name": p["metadata"]["name"],
            "phase": p["status"].get("phase"),
            "ready": bool(statuses) and all(s["ready"] for s in statuses),
            "restarts": sum(s["restartCount"] for s in statuses),
            "started": p["status"].get("startTime"),
            "last_stop": last and {"reason": last.get("reason"), "exit_code": last.get("exitCode"), "at": last.get("finishedAt")},
        })
    return sorted(pods, key=lambda p: p["name"])


# k8s의 자원 표기 → 숫자. CPU는 밀리코어(1코어 = 1000m), 메모리는 MiB
def _cpu_m(q):
    if not q:
        return None
    units = {"n": 1e-6, "u": 1e-3, "m": 1}
    return float(q[:-1]) * units[q[-1]] if q[-1] in units else float(q) * 1000


def _mem_mib(q):
    if not q:
        return None
    for unit, mib in (("Ki", 1 / 1024), ("Mi", 1), ("Gi", 1024), ("k", 1000 / 2**20), ("M", 1e6 / 2**20), ("G", 1e9 / 2**20)):
        if q.endswith(unit):
            return float(q[: -len(unit)]) * mib
    return float(q) / 2**20


@app.get("/resources", dependencies=[Depends(check_token)])
def resources():
    """노드(이 PC의 WSL)와 파드별 CPU·메모리 사용량. metrics-server가 15초쯤마다 잰 값이라 '지금 이 순간'은 아니에요
    노드 값에는 k8s 밖의 Ollama·automachine도 들어 있어요 (같은 WSL을 나눠 써요)"""
    try:
        node_list = k8s.get("/api/v1/nodes")["items"]
        pods = k8s.get(k8s.ns("pods"))["items"]
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"k8s API에 묻지 못했어요: {type(exc).__name__}")
    try:
        node_use = {n["metadata"]["name"]: n["usage"] for n in k8s.get("/apis/metrics.k8s.io/v1beta1/nodes")["items"]}
        pod_use = {p["metadata"]["name"]: p["containers"] for p in k8s.get(k8s.ns("pods", "/apis/metrics.k8s.io/v1beta1"))["items"]}
        metrics = True
    except httpx.HTTPError:
        node_use, pod_use, metrics = {}, {}, False   # metrics-server가 꺼져 있어도 나머지는 보여 줘요

    nodes = [{
        "name": n["metadata"]["name"],
        "cpu_m": _cpu_m(node_use.get(n["metadata"]["name"], {}).get("cpu")),
        "cpu_total_m": _cpu_m(n["status"]["allocatable"]["cpu"]),
        "mem_mib": _mem_mib(node_use.get(n["metadata"]["name"], {}).get("memory")),
        "mem_total_mib": _mem_mib(n["status"]["allocatable"]["memory"]),
    } for n in node_list]

    rows = []
    for p in pods:
        if p["status"].get("phase") != "Running":
            continue   # 끝난 Job 파드(백업·사전 적재)는 자원을 안 써요
        name = p["metadata"]["name"]
        used = pod_use.get(name, [])
        limits = [c.get("resources", {}).get("limits", {}) for c in p["spec"]["containers"]]
        rows.append({
            "name": name,
            "cpu_m": sum(_cpu_m(c["usage"]["cpu"]) for c in used) if used else None,
            "cpu_limit_m": sum(_cpu_m(l.get("cpu")) or 0 for l in limits) or None,
            "mem_mib": sum(_mem_mib(c["usage"]["memory"]) for c in used) if used else None,
            "mem_limit_mib": sum(_mem_mib(l.get("memory")) or 0 for l in limits) or None,
        })
    return {"metrics": metrics, "nodes": nodes, "pods": sorted(rows, key=lambda r: r["name"])}


def _dict_jobs():
    jobs = [j for j in k8s.get(k8s.ns("jobs", "/apis/batch/v1"))["items"] if j["metadata"]["name"].startswith("dict-load")]
    jobs.sort(key=lambda j: j["status"].get("startTime") or "", reverse=True)
    return [{
        "name": j["metadata"]["name"],
        "started": j["status"].get("startTime"),
        "finished": j["status"].get("completionTime"),
        "state": "완료" if j["status"].get("succeeded") else "실패" if j["status"].get("failed") else "진행 중",
    } for j in jobs[:3]]


def _cronjobs():
    return [{
        "name": c["metadata"]["name"],
        "schedule": c["spec"]["schedule"],
        "suspend": c["spec"].get("suspend", False),
        "last": c["status"].get("lastSuccessfulTime"),
    } for c in k8s.get(k8s.ns("cronjobs", "/apis/batch/v1"))["items"]]


@app.get("/status", dependencies=[Depends(check_token)])
def status():
    try:
        return {"workloads": _workloads(), "pods": _pods(), "dict_jobs": _dict_jobs(), "cronjobs": _cronjobs()}
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"k8s API에 묻지 못했어요: {type(exc).__name__}")


@app.post("/restart/{name}", dependencies=[Depends(check_token)])
def restart(name: str):
    """kubectl rollout restart와 같아요: 파드 설계도에 '다시 시작한 시각'을 적으면 k8s가 새 파드로 하나씩 갈아 끼워요"""
    if name not in RESTARTABLE:
        raise HTTPException(status_code=404, detail="다시 시작할 수 없는 이름이에요.")
    now = datetime.now(timezone.utc).isoformat()
    k8s.patch(k8s.ns(f"deployments/{name}", "/apis/apps/v1"),
              {"spec": {"template": {"metadata": {"annotations": {"kubectl.kubernetes.io/restartedAt": now}}}}})
    return {"ok": True, "name": name, "at": now}


@app.post("/dict-reload", dependencies=[Depends(check_token)])
def dict_reload():
    """사전 다시 적재: 멈춰 둔 dict-load CronJob의 설계도를 복사해서 Job을 하나 만들어요
    (kubectl create job --from=cronjob/dict-load 와 같아요)
    CSV는 마지막 배포 때 ConfigMap에 넣은 것이에요. 새 CSV를 넣으려면 PR 머지 뒤 다시 배포해요"""
    return {"ok": True, "job": _job_from_cron("dict-load")}


def _job_from_cron(cron_name):
    """CronJob 설계도를 복사해서 Job을 지금 하나 만들어요. 이름은 코드에 적힌 둘(dict-load·db-backup)만 써요
    주인(ownerReferences)을 CronJob으로 적어서, kubectl create job --from처럼 CronJob의 기록 개수 제한에 같이 묶여요"""
    cron = k8s.get(k8s.ns(f"cronjobs/{cron_name}", "/apis/batch/v1"))
    name = f"{cron_name}-manual-" + datetime.now(timezone.utc).strftime("%m%d%H%M%S")
    k8s.post(k8s.ns("jobs", "/apis/batch/v1"), {
        "apiVersion": "batch/v1",
        "kind": "Job",
        "metadata": {
            "name": name,
            "annotations": {"cronjob.kubernetes.io/instantiate": "manual"},
            "ownerReferences": [{"apiVersion": "batch/v1", "kind": "CronJob", "name": cron_name,
                                 "uid": cron["metadata"]["uid"], "controller": True}],
        },
        "spec": cron["spec"]["jobTemplate"]["spec"],
    })
    return name


def _job_state(job):
    status = job.get("status", {})
    for c in status.get("conditions", []):
        if c.get("status") == "True" and c.get("type") in ("Complete", "Failed"):
            return "성공" if c["type"] == "Complete" else "실패"
    return "진행 중"


def _backup_files():
    # 다 읽어 본 뒤에야 db_*.dump 이름이 붙어요 (k8s/backup.yaml). 만드는 중인 .tmp는 세지 않아요
    try:
        found = sorted(Path(BACKUP_PATH).glob("db_*.dump"), key=lambda f: f.stat().st_mtime, reverse=True)
        return [{
            "name": f.name,
            "size_mib": round(f.stat().st_size / MIB, 2),
            "at": datetime.fromtimestamp(f.stat().st_mtime, timezone.utc).isoformat(),
        } for f in found]
    except OSError:
        return []


@app.get("/backups", dependencies=[Depends(check_token)])
def backups():
    """백업 파일과 예약 상태, DB 저장 공간(PVC) 크기. DB 안의 크기는 DB 계정이 있는 백엔드가 따로 봐요"""
    files = _backup_files()
    try:
        cron = k8s.get(k8s.ns("cronjobs/db-backup", "/apis/batch/v1"))
        jobs = [j for j in k8s.get(k8s.ns("jobs", "/apis/batch/v1"))["items"]
                if any(o.get("name") == "db-backup" for o in j["metadata"].get("ownerReferences", []))]
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"k8s API에 묻지 못했어요: {type(exc).__name__}")
    latest = max(jobs, key=lambda j: j["metadata"]["creationTimestamp"], default=None)
    try:
        capacity = k8s.get(k8s.ns("persistentvolumeclaims/pgdata-db-0"))["status"]["capacity"]["storage"]
    except (httpx.HTTPError, KeyError):
        capacity = None
    return {
        "files": files,
        "schedule": cron["spec"]["schedule"],
        "time_zone": cron["spec"].get("timeZone"),
        "last_job": latest and {
            "name": latest["metadata"]["name"],
            "state": _job_state(latest),
            "created": latest["metadata"]["creationTimestamp"],
            "manual": latest["metadata"].get("annotations", {}).get("cronjob.kubernetes.io/instantiate") == "manual",
        },
        "running": any(_job_state(j) == "진행 중" for j in jobs),
        "pvc_capacity": capacity,   # 예: "5Gi"
    }


@app.post("/backup-now", dependencies=[Depends(check_token)])
def backup_now():
    """지금 백업: db-backup CronJob 설계도로 Job을 하나 만들어요. 이미 돌고 있으면 겹치지 않게 거절해요"""
    if backups()["running"]:
        raise HTTPException(status_code=409, detail="백업이 이미 진행 중이에요. 끝난 뒤 다시 해 주세요.")
    return {"ok": True, "job": _job_from_cron("db-backup")}
