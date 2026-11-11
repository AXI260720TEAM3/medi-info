-- AI 답변 검증 기록 (관리자 대시보드 "AI 답변 검증"). chat_answer.py가 첫 답을 검사한 결과를 질문 기록에 함께 남긴다
-- 새 DB는 자동 실행, 기존 DB는 이 파일을 한 번 실행하면 된다(k8s는 deploy.sh가 매번 실행). 여러 번 실행해도 안전하다.
ALTER TABLE public.chat_log
    ADD COLUMN IF NOT EXISTS check_result character varying(12)
        CONSTRAINT ck_chat_log_check_result CHECK (check_result IN ('pass', 'retry_pass', 'fallback')),
    ADD COLUMN IF NOT EXISTS check_reason character varying(60),
    ADD COLUMN IF NOT EXISTS retry_reason character varying(60),
    ADD COLUMN IF NOT EXISTS rejected_draft text,
    ADD COLUMN IF NOT EXISTS retry_ms integer;

COMMENT ON COLUMN public.chat_log.check_result IS 'AI 답변 검증 결과: pass(첫 답 통과), retry_pass(다시 써서 통과), fallback(정해진 안내로 대체). AI를 안 부른 답은 NULL';
COMMENT ON COLUMN public.chat_log.check_reason IS '첫 답이 걸린 사유';
COMMENT ON COLUMN public.chat_log.retry_reason IS '다시 쓴 답도 걸렸을 때 사유';
COMMENT ON COLUMN public.chat_log.rejected_draft IS '막힌 첫 초안 (사용자에게 안 보냄, 개인정보 모양은 가림, 질문 기록과 함께 90일 뒤 삭제)';
COMMENT ON COLUMN public.chat_log.retry_ms IS '다시 쓰는 데 걸린 시간(ms)';
