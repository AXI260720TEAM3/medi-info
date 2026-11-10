"""k8s API 부르기. 파드에 들어 있는 이 서비스 전용 계정(ServiceAccount) 토큰을 써요
할 수 있는 일은 k8s/ops.yaml의 Role이 정해요. 여기서 실수로 다른 일을 시켜도 k8s가 거절해요 (403)"""
from pathlib import Path

import httpx

ACCOUNT = Path("/var/run/secrets/kubernetes.io/serviceaccount")
API = "https://kubernetes.default.svc"
NAMESPACE = "medi-info"


def _request(method, path, headers=None, **kwargs):
    # 토큰은 k8s가 주기적으로 바꿔서 매번 새로 읽어요
    headers = {"Authorization": f"Bearer {(ACCOUNT / 'token').read_text()}", **(headers or {})}
    res = httpx.request(method, f"{API}{path}", headers=headers, verify=str(ACCOUNT / "ca.crt"), timeout=5, **kwargs)
    res.raise_for_status()
    return res.json()


def get(path):
    return _request("GET", path)


def post(path, body):
    return _request("POST", path, json=body)


def patch(path, body):
    """바꿀 칸만 보내면 k8s가 합쳐 줘요 (strategic merge patch)"""
    return _request("PATCH", path, json=body, headers={"Content-Type": "application/strategic-merge-patch+json"})


def ns(resource, group="/api/v1"):
    return f"{group}/namespaces/{NAMESPACE}/{resource}"
