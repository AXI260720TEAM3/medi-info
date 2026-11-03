-- 이메일 인증번호 (가입 인증, 아이디 찾기, 비밀번호 재설정)
-- 새 DB는 자동 실행, 기존 DB는 이 파일을 한 번 실행하면 된다. 여러 번 실행해도 안전하다.
CREATE TABLE IF NOT EXISTS public.email_code(
    code_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    email character varying(255) NOT NULL,
    purpose character varying(10) NOT NULL,
    code_hash character(64) NOT NULL,
    attempts smallint DEFAULT 0 NOT NULL,
    expires_at timestamp with time zone NOT NULL,
    used_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ck_email_code_purpose CHECK (purpose IN ('signup', 'find_id', 'reset_pw'))
);

CREATE INDEX IF NOT EXISTS ix_email_code_lookup ON public.email_code (email, purpose, created_at DESC);

COMMENT ON TABLE public.email_code IS '이메일 인증번호';
COMMENT ON COLUMN public.email_code.code_hash IS '인증번호 해시 (원래 번호는 저장하지 않음)';
COMMENT ON COLUMN public.email_code.attempts IS '틀린 횟수';
COMMENT ON COLUMN public.email_code.used_at IS '사용한 시각 (한 번 쓰면 다시 못 씀)';