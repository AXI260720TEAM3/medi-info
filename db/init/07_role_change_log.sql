-- 관리자 계정 탭 (11/12): 권한(role)을 누가 언제 바꿨는지 남긴다
-- 새 DB는 자동 실행, 기존 DB는 이 파일을 한 번 실행하면 된다(k8s는 deploy.sh가 매번 실행). 여러 번 실행해도 안전하다.
-- 아이디는 그때 값을 글자로도 남긴다: 계정을 지워도(탈퇴) 기록은 남고, 사용자ID 칸만 비워진다(SET NULL)
CREATE TABLE IF NOT EXISTS public.role_change_log (
    change_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    target_user_id bigint REFERENCES public.app_user (user_id) ON DELETE SET NULL,
    target_login_id character varying(50) NOT NULL,
    changed_by_user_id bigint REFERENCES public.app_user (user_id) ON DELETE SET NULL,
    changed_by_login_id character varying(50) NOT NULL,
    old_role character varying(10) NOT NULL,
    new_role character varying(10) NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);

COMMENT ON TABLE public.role_change_log IS '권한 변경 기록 (관리자 계정 탭)';
COMMENT ON COLUMN public.role_change_log.target_login_id IS '바뀐 계정의 아이디 (그때 값)';
COMMENT ON COLUMN public.role_change_log.changed_by_login_id IS '바꾼 관리자의 아이디 (그때 값)';

CREATE INDEX IF NOT EXISTS ix_role_change_log_created ON public.role_change_log (created_at DESC);
