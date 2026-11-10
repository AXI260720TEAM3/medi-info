import copy
import time
from functools import wraps
from threading import Lock

# 공공 API 응답을 잠깐 기억해 두는 장치 (e약은요가 0.5~10초로 들쭉날쭉해서, 같은 질문은 다시 묻지 않기)
#   @ttl_cache(3600)          ← 1시간 동안 기억
#   def get_by_seq(item_seq): ...
# - 함수 인자가 같으면 같은 질문으로 봐요 (인자는 글자·숫자처럼 바뀌지 않는 값이어야 해요)
# - 오류가 나면 기억하지 않아요 (실패를 기억하면 그동안 계속 실패하니까)
# - 기억한 값은 복사해서 돌려줘요 (부르는 쪽이 목록을 정렬하거나 고쳐도 기억한 원본은 그대로)
# - 백엔드 파드마다 따로 기억해요. 파드가 여러 개가 되면(HPA) 각자 한 번씩은 API를 불러요


def ttl_cache(seconds, maxsize=1000):
    def deco(fn):
        store = {}      # 질문(key) → (만료 시각, 답)
        lock = Lock()   # FastAPI는 요청을 여러 스레드에서 처리해서, 동시에 store를 고치지 않게

        @wraps(fn)
        def wrapper(*args, **kwargs):
            key = (args, tuple(sorted(kwargs.items())))
            now = time.monotonic()
            with lock:
                hit = store.get(key)
                if hit is not None and hit[0] > now:
                    return copy.deepcopy(hit[1])

            value = fn(*args, **kwargs)   # 기억이 없거나 만료됨 → 진짜로 API 부르기 (오류면 여기서 끝, 기억 안 함)
            with lock:
                if len(store) >= maxsize:  # 너무 많이 쌓이면 통째로 비워요 (간단하게)
                    store.clear()
                store[key] = (now + seconds, value)
            return copy.deepcopy(value)

        wrapper.cache_clear = store.clear   # 시험할 때 기억 지우기: get_by_seq.cache_clear()
        return wrapper
    return deco
