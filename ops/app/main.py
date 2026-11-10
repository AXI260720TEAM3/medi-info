"""medi-info 운영 API (기능명세 H-5). 관리자 화면의 운영 탭이 백엔드를 거쳐 불러요
- 바깥에서 바로 오는 길(Ingress)이 없어요. 같은 클러스터의 백엔드 파드만 들어올 수 있어요 (NetworkPolicy)
- 백엔드는 관리자 확인을 한 뒤 X-Ops-Token을 붙여서 불러요. 토큰이 없거나 틀리면 401
- 할 수 있는 일: 상태 보기, backend·web 다시 시작, 사전 다시 적재(dict-load Job)"""
import os
import secrets
from datetime import datetime, timezone

import httpx
from fastapi import Depends, FastAPI, Header, HTTPException

from . import k8s

OPS_TOKEN = os.environ["OPS_TOKEN"]   # 없으면 켜지지 않아요 (토큰 없이 열린 운영 API는 위험해서)
RESTARTABLE = ("backend", "web")      # Role도 이 두 이름만 patch를 허락해요


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
        pods.append({
            "name": p["metadata"]["name"],
            "phase": p["status"].get("phase"),
            "ready": bool(statuses) and all(s["ready"] for s in statuses),
            "restarts": sum(s["restartCount"] for s in statuses),
            "started": p["status"].get("startTime"),
        })
    return sorted(pods, key=lambda p: p["name"])


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
    cron = k8s.get(k8s.ns("cronjobs/dict-load", "/apis/batch/v1"))
    name = "dict-load-manual-" + datetime.now(timezone.utc).strftime("%m%d%H%M%S")
    k8s.post(k8s.ns("jobs", "/apis/batch/v1"), {
        "apiVersion": "batch/v1",
        "kind": "Job",
        "metadata": {"name": name, "annotations": {"cronjob.kubernetes.io/instantiate": "manual"}},
        "spec": cron["spec"]["jobTemplate"]["spec"],
    })
    return {"ok": True, "job": name}
