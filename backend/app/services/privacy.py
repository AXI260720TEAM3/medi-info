import re

from sqlalchemy import text

from ..database import SessionLocal

# 질문 기록(chat_log) 개인정보 처리 (기능명세 I-7, 11/06 기획 피드백 "개인정보법 확인")
# - 질문 기록에는 처음부터 사용자 ID를 넣지 않아요(누구 질문인지 모름). 남은 위험은 "글 안의 개인정보"
# - 그래서 저장하기 전에 전화번호·이메일·주민번호 모양을 가리고, 보관 기간이 지나면 지워요

RETENTION_DAYS = 90   # 질문 기록 보관 기간 (처리방침 화면 /privacy 에도 같은 숫자)

# 주민등록번호: 900101-1234567, 9001011234567
RRN = re.compile(r"\d{6}-?[1-4]\d{6}")


def mask_personal(text_):
    """글 안의 개인정보 모양을 가린다. 주민번호 -> ******-*******, 전화번호 -> ***-****-****, 이메일 -> ***@***"""
    text_ = RRN.sub("******-*******", text_)   # 주민번호를 먼저 (숫자가 길어서 전화번호로 잘못 잡히지 않게)
    text_ = re.sub(r"01[016789]-?\d{3,4}-?\d{4}", "***-****-****", text_)
    text_ = re.sub(r"[\w.+-]+@[\w-]+\.[\w.]+", "***@***", text_)
    return text_


def purge_old_chat_logs(days=RETENTION_DAYS):
    """보관 기간이 지난 질문 기록을 지우고, 지운 줄 수를 돌려준다"""
    with SessionLocal() as db:
        result = db.execute(
            text("DELETE FROM chat_log WHERE created_at < now() - make_interval(days => :days)"),
            {"days": days},
        )
        db.commit()
        return result.rowcount


# 백엔드 컨테이너에서 직접 실행: python -m app.services.privacy  (나중에 k8s CronJob이 매일 이걸 돌려요)
if __name__ == "__main__":
    print(f"보관 기간({RETENTION_DAYS}일)이 지난 질문 기록 {purge_old_chat_logs()}줄을 지웠어요")
