-- 관리자 질문 기록 표 (11/11): 약 이름·시험 표시 칸, 질문 종류에 '약확인' 추가
-- 새 DB는 자동 실행, 기존 DB는 이 파일을 한 번 실행하면 된다(k8s는 deploy.sh가 매번 실행). 여러 번 실행해도 안전하다.
ALTER TABLE public.chat_log
    ADD COLUMN IF NOT EXISTS item_name character varying(200),
    ADD COLUMN IF NOT EXISTS is_test boolean DEFAULT false NOT NULL;

COMMENT ON COLUMN public.chat_log.item_name IS '답의 기준 약 이름 (관리자 표의 약 칸)';
COMMENT ON COLUMN public.chat_log.is_test IS '평가·시험 요청 (X-Medi-Test: 1). 관리자 기록·통계에서 기본으로 뺌';

-- 약확인: 어느 약인지 되물은 답 (약 이름만 적었거나, 같은 이름이 여러 개거나, 못 찾음). 예전엔 NULL(분류 못 함)로 남았다
ALTER TABLE public.chat_log DROP CONSTRAINT IF EXISTS ck_chat_log_type;
ALTER TABLE public.chat_log ADD CONSTRAINT ck_chat_log_type
    CHECK (question_type IN ('약정보', '함께먹기', '증상', '차단', '약확인'));

-- 지난 기록도 같은 기준으로: routes/chat.py ask_which_drug가 쓰는 네 문장으로 시작하는 답
UPDATE public.chat_log SET question_type = '약확인'
WHERE question_type IS NULL AND NOT blocked AND (
    answer LIKE '검색된 약 중 정확한 제품을 선택해 주세요%'
    OR answer LIKE '같은 이름의 약이 여러 개예요%'
    OR answer LIKE '질문에서 정확한 의약품을 찾지 못했어요%'
    OR answer LIKE '어떤 약에 대한 질문인지 확인이 필요해요%'
);

CREATE INDEX IF NOT EXISTS ix_chat_log_created ON public.chat_log (created_at DESC);
