"""서비스별 요청 지표 (automachine ops/app/traffic.py를 옮겨 옴)
Traefik이 내보내는 누적 숫자를 15초마다 읽어 두고, 두 시점의 차이로 초당 요청·오류·응답 시간을 계산해요.

- Prometheus를 띄우지 않아요. WSL 메모리가 8GB뿐이라서요. 기록은 메모리에만 있어서 ops가 다시 켜지면 사라져요(최근 5분만).
- Traefik을 거친 요청만 보여요(브라우저·휴대폰에서 온 것). 파드끼리 직접 부르는 요청(backend → ops, 파드 안 평가)은 안 세요.
- automachine과 같은 Traefik을 써서, medi-info 서비스만 골라요. 입구 전체 숫자는 두 프로젝트가 섞여서 쓰지 않아요.
"""
import math
import os
import re
import threading
import time
from collections import deque

import httpx

# 10.42.0.1은 파드에서 본 이 PC. Traefik은 PC의 네트워크에서 돌아요 (k8s/cluster/traefik-config.yaml)
URL = os.environ.get("TRAEFIK_METRICS_URL", "http://10.42.0.1:9100/metrics")
INTERVAL_S = 15
SHORT_S = 60    # 초당 요청·오류·응답 시간
LONG_S = 300    # 서버 오류는 5분 합도 따로 (가끔 나는 500을 놓치지 않게)

_LINE = re.compile(
    r"^(traefik_service_requests_total|traefik_service_request_duration_seconds_bucket)"
    r"\{([^}]*)\} (\S+)$")
_LABEL = re.compile(r'(\w+)="([^"]*)"')
_SERVICE = re.compile(r"^medi-info-(.+)-\d+@kubernetes$")   # medi-info-backend-8000@kubernetes → backend

_samples = deque(maxlen=LONG_S // INTERVAL_S + 1)
_error = None
EMPTY = {"codes": {}, "buckets": {}}


def parse(text):
    """서비스별 {codes: {응답 코드: 누적}, buckets: {le: 누적}}"""
    services = {}
    for line in text.splitlines():
        match = _LINE.match(line)
        if not match:
            continue
        labels = dict(_LABEL.findall(match[2]))
        if labels.get("protocol") != "http":
            continue
        service = _SERVICE.match(labels.get("service", ""))
        if not service:
            continue
        entry = services.setdefault(service[1], {"codes": {}, "buckets": {}})
        value = float(match[3])
        if match[1] == "traefik_service_requests_total":
            entry["codes"][labels["code"]] = entry["codes"].get(labels["code"], 0) + value
        else:
            entry["buckets"][labels["le"]] = entry["buckets"].get(labels["le"], 0) + value
    return services


def _total(entry):
    return sum(entry["codes"].values())


def _restarted(older, newer):
    """누적 숫자가 줄었으면 Traefik이 다시 켜진 것. 그 앞 기록과는 뺄 수 없어요"""
    return any(_total(entry) > _total(newer.get(name, EMPTY)) for name, entry in older.items())


def _baseline(samples, seconds):
    """가장 최근 기록에서 seconds 안의 가장 오래된 기록 (Traefik 재시작 전으로는 안 넘어가요)"""
    newest = samples[-1]
    base = newest
    for sample in reversed(samples[:-1]):
        too_old = base is not newest and newest["at"] - sample["at"] > seconds + 1
        if too_old or _restarted(sample["services"], base["services"]):
            break
        base = sample
    return base


def _count(new, old, prefix):
    return int(sum(v - old["codes"].get(c, 0) for c, v in new["codes"].items() if c.startswith(prefix)))


def _p95(new, old):
    """Traefik의 칸이 0.1·0.3·1.2·5초로 넓어서, 추정값 대신 '95%가 이 안에 든 칸'을 돌려줘요"""
    changes = sorted(((float(le), v - old["buckets"].get(le, 0)) for le, v in new["buckets"].items()), key=lambda c: c[0])
    if not changes or changes[-1][1] <= 0:
        return None
    for le, cumulative in changes:
        if cumulative >= changes[-1][1] * 0.95:
            return le
    return None


def summarize(samples):
    if len(samples) < 2:
        return []
    newest = samples[-1]
    short, long = _baseline(samples, SHORT_S), _baseline(samples, LONG_S)
    elapsed = newest["at"] - short["at"]
    views = []
    for name, entry in sorted(newest["services"].items()):
        recent = short["services"].get(name, EMPTY)
        requests = int(_total(entry) - _total(recent))
        p95 = _p95(entry, recent)
        over = p95 == math.inf   # 맨 끝 칸(+Inf, 5초 넘음). JSON에는 Infinity를 못 담아요
        views.append({
            "name": name,
            "requests": requests,
            "per_second": requests / elapsed if elapsed > 0 else 0,
            "client_errors": _count(entry, recent, "4"),
            "server_errors": _count(entry, recent, "5"),
            "server_errors_long": _count(entry, long["services"].get(name, EMPTY), "5"),
            "p95_le": None if over else p95,
            "p95_over": over,
        })
    return views


def status():
    samples = list(_samples)
    return {
        "available": _error is None,
        "error": _error,
        "window_s": int(samples[-1]["at"] - _baseline(samples, SHORT_S)["at"]) if samples else 0,
        "long_window_s": int(samples[-1]["at"] - _baseline(samples, LONG_S)["at"]) if samples else 0,
        "services": summarize(samples),
    }


def _collect():
    global _error
    while True:
        try:
            res = httpx.get(URL, timeout=5)
            res.raise_for_status()
            _samples.append({"at": time.monotonic(), "services": parse(res.text)})
            _error = None
        except httpx.HTTPError as exc:
            _error = type(exc).__name__
        time.sleep(INTERVAL_S)


def start():
    threading.Thread(target=_collect, daemon=True).start()
