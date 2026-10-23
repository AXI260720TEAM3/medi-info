--
-- PostgreSQL database dump
--

\restrict oB4tLuDd6y37wTo8gNbJuXfNXp5tDs2NQwZopaBLos3RJukh4j6y2oChUlPLYhE

-- Dumped from database version 16.15 (Ubuntu 16.15-0ubuntu0.24.04.1)
-- Dumped by pg_dump version 16.15 (Ubuntu 16.15-0ubuntu0.24.04.1)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: pg_trgm; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS pg_trgm WITH SCHEMA public;


--
-- Name: EXTENSION pg_trgm; Type: COMMENT; Schema: -; Owner: -
--

COMMENT ON EXTENSION pg_trgm IS 'text similarity measurement and index searching based on trigrams';


--
-- Name: vector; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS vector WITH SCHEMA public;


--
-- Name: EXTENSION vector; Type: COMMENT; Schema: -; Owner: -
--

COMMENT ON EXTENSION vector IS 'vector data type and ivfflat and hnsw access methods';


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: app_user; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.app_user (
    user_id bigint NOT NULL,
    login_id character varying(50) NOT NULL,
    password_hash character varying(255) NOT NULL,
    role character varying(10) DEFAULT 'user'::character varying NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ck_app_user_role CHECK (((role)::text = ANY ((ARRAY['user'::character varying, 'admin'::character varying])::text[])))
);


--
-- Name: TABLE app_user; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.app_user IS '사용자';


--
-- Name: COLUMN app_user.user_id; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.app_user.user_id IS '사용자ID';


--
-- Name: COLUMN app_user.login_id; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.app_user.login_id IS '로그인ID';


--
-- Name: COLUMN app_user.password_hash; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.app_user.password_hash IS '비밀번호해시';


--
-- Name: COLUMN app_user.role; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.app_user.role IS '권한 (user/admin)';


--
-- Name: COLUMN app_user.created_at; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.app_user.created_at IS '가입일시';


--
-- Name: app_user_user_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.app_user_user_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: app_user_user_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.app_user_user_id_seq OWNED BY public.app_user.user_id;


--
-- Name: caution_keyword; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.caution_keyword (
    keyword_id integer NOT NULL,
    keyword character varying(100) NOT NULL,
    target character varying(10) NOT NULL,
    CONSTRAINT ck_caution_keyword_target CHECK (((target)::text = ANY ((ARRAY['임부'::character varying, '수유'::character varying, '소아'::character varying, '노인'::character varying, '복용중'::character varying])::text[])))
);


--
-- Name: TABLE caution_keyword; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.caution_keyword IS '주의 대상 키워드';


--
-- Name: COLUMN caution_keyword.keyword_id; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.caution_keyword.keyword_id IS '키워드ID';


--
-- Name: COLUMN caution_keyword.keyword; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.caution_keyword.keyword IS '표현';


--
-- Name: COLUMN caution_keyword.target; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.caution_keyword.target IS '대상';


--
-- Name: caution_keyword_keyword_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.caution_keyword_keyword_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: caution_keyword_keyword_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.caution_keyword_keyword_id_seq OWNED BY public.caution_keyword.keyword_id;


--
-- Name: chat_log; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.chat_log (
    log_id bigint NOT NULL,
    session_id character varying(64),
    user_id bigint,
    question text NOT NULL,
    answer text,
    question_type character varying(20),
    target_item_seq character varying(20),
    blocked boolean DEFAULT false NOT NULL,
    block_reason character varying(50),
    model character varying(100),
    prompt_version character varying(20),
    sources jsonb,
    response_ms integer,
    feedback smallint,
    reported boolean DEFAULT false NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ck_chat_log_feedback CHECK ((feedback = ANY (ARRAY['-1'::integer, 1]))),
    CONSTRAINT ck_chat_log_type CHECK (((question_type)::text = ANY ((ARRAY['약정보'::character varying, '함께먹기'::character varying, '증상'::character varying, '차단'::character varying])::text[])))
);


--
-- Name: TABLE chat_log; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.chat_log IS '질문 기록';


--
-- Name: COLUMN chat_log.log_id; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.chat_log.log_id IS '기록ID';


--
-- Name: COLUMN chat_log.session_id; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.chat_log.session_id IS '세션ID';


--
-- Name: COLUMN chat_log.user_id; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.chat_log.user_id IS '사용자ID';


--
-- Name: COLUMN chat_log.question; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.chat_log.question IS '질문';


--
-- Name: COLUMN chat_log.answer; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.chat_log.answer IS '답변';


--
-- Name: COLUMN chat_log.question_type; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.chat_log.question_type IS '질문종류';


--
-- Name: COLUMN chat_log.target_item_seq; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.chat_log.target_item_seq IS '지정약품목기준코드 (상세에서 질문 시)';


--
-- Name: COLUMN chat_log.blocked; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.chat_log.blocked IS '차단여부';


--
-- Name: COLUMN chat_log.block_reason; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.chat_log.block_reason IS '차단사유';


--
-- Name: COLUMN chat_log.model; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.chat_log.model IS '사용모델';


--
-- Name: COLUMN chat_log.prompt_version; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.chat_log.prompt_version IS '프롬프트버전';


--
-- Name: COLUMN chat_log.sources; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.chat_log.sources IS '출처목록';


--
-- Name: COLUMN chat_log.response_ms; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.chat_log.response_ms IS '응답시간(ms)';


--
-- Name: COLUMN chat_log.feedback; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.chat_log.feedback IS '피드백 (1=좋아요, -1=싫어요)';


--
-- Name: COLUMN chat_log.reported; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.chat_log.reported IS '틀린정보신고여부';


--
-- Name: COLUMN chat_log.created_at; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.chat_log.created_at IS '질문일시';


--
-- Name: chat_log_log_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.chat_log_log_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: chat_log_log_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.chat_log_log_id_seq OWNED BY public.chat_log.log_id;


--
-- Name: drug; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.drug (
    item_seq character varying(20) NOT NULL,
    item_name character varying(300) NOT NULL,
    entp_name character varying(200),
    etc_otc character varying(10) DEFAULT '일반'::character varying NOT NULL,
    data_source character varying(20) DEFAULT 'e약은요'::character varying NOT NULL,
    efcy text,
    use_method text,
    atpn_warn text,
    atpn text,
    intrc text,
    se text,
    deposit text,
    item_image character varying(500),
    update_de date,
    raw_json jsonb,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ck_drug_etc_otc CHECK (((etc_otc)::text = ANY ((ARRAY['일반'::character varying, '전문'::character varying])::text[]))),
    CONSTRAINT ck_drug_source CHECK (((data_source)::text = ANY ((ARRAY['e약은요'::character varying, '허가정보'::character varying, '수동'::character varying])::text[])))
);


--
-- Name: TABLE drug; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.drug IS '약 기본 정보';


--
-- Name: COLUMN drug.item_seq; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.drug.item_seq IS '품목기준코드';


--
-- Name: COLUMN drug.item_name; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.drug.item_name IS '제품명';


--
-- Name: COLUMN drug.entp_name; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.drug.entp_name IS '업체명';


--
-- Name: COLUMN drug.etc_otc; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.drug.etc_otc IS '전문일반구분';


--
-- Name: COLUMN drug.data_source; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.drug.data_source IS '데이터출처';


--
-- Name: COLUMN drug.efcy; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.drug.efcy IS '효능';


--
-- Name: COLUMN drug.use_method; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.drug.use_method IS '사용법';


--
-- Name: COLUMN drug.atpn_warn; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.drug.atpn_warn IS '경고';


--
-- Name: COLUMN drug.atpn; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.drug.atpn IS '주의사항';


--
-- Name: COLUMN drug.intrc; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.drug.intrc IS '상호작용';


--
-- Name: COLUMN drug.se; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.drug.se IS '부작용';


--
-- Name: COLUMN drug.deposit; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.drug.deposit IS '보관법';


--
-- Name: COLUMN drug.item_image; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.drug.item_image IS '낱알이미지주소';


--
-- Name: COLUMN drug.update_de; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.drug.update_de IS '갱신일';


--
-- Name: COLUMN drug.raw_json; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.drug.raw_json IS '응답원본';


--
-- Name: COLUMN drug.created_at; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.drug.created_at IS '등록일시';


--
-- Name: COLUMN drug.updated_at; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.drug.updated_at IS '수정일시';


--
-- Name: drug_chunk; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.drug_chunk (
    chunk_id bigint NOT NULL,
    item_seq character varying(20) NOT NULL,
    section character varying(20) NOT NULL,
    content text NOT NULL,
    embedding public.vector(1024),
    update_de date,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ck_drug_chunk_section CHECK (((section)::text = ANY ((ARRAY['효능'::character varying, '사용법'::character varying, '경고'::character varying, '주의사항'::character varying, '상호작용'::character varying, '부작용'::character varying, '보관법'::character varying])::text[])))
);


--
-- Name: TABLE drug_chunk; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.drug_chunk IS '약 항목 조각 (RAG)';


--
-- Name: COLUMN drug_chunk.chunk_id; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.drug_chunk.chunk_id IS '조각ID';


--
-- Name: COLUMN drug_chunk.item_seq; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.drug_chunk.item_seq IS '품목기준코드';


--
-- Name: COLUMN drug_chunk.section; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.drug_chunk.section IS '항목';


--
-- Name: COLUMN drug_chunk.content; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.drug_chunk.content IS '원문';


--
-- Name: COLUMN drug_chunk.embedding; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.drug_chunk.embedding IS '임베딩 (bge-m3 1024차원)';


--
-- Name: COLUMN drug_chunk.update_de; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.drug_chunk.update_de IS '원본갱신일';


--
-- Name: COLUMN drug_chunk.created_at; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.drug_chunk.created_at IS '등록일시';


--
-- Name: drug_chunk_chunk_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.drug_chunk_chunk_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: drug_chunk_chunk_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.drug_chunk_chunk_id_seq OWNED BY public.drug_chunk.chunk_id;


--
-- Name: drug_ingredient; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.drug_ingredient (
    item_seq character varying(20) NOT NULL,
    ingr_id integer NOT NULL,
    amount character varying(100),
    data_source character varying(20) DEFAULT '허가정보'::character varying NOT NULL,
    CONSTRAINT ck_drug_ingredient_source CHECK (((data_source)::text = ANY ((ARRAY['허가정보'::character varying, '제품명'::character varying, '수동'::character varying])::text[])))
);


--
-- Name: TABLE drug_ingredient; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.drug_ingredient IS '약 성분 구성';


--
-- Name: COLUMN drug_ingredient.item_seq; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.drug_ingredient.item_seq IS '품목기준코드';


--
-- Name: COLUMN drug_ingredient.ingr_id; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.drug_ingredient.ingr_id IS '성분ID';


--
-- Name: COLUMN drug_ingredient.amount; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.drug_ingredient.amount IS '함량';


--
-- Name: COLUMN drug_ingredient.data_source; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.drug_ingredient.data_source IS '데이터출처 (허가정보/제품명 괄호/수동)';


--
-- Name: dur_rule; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.dur_rule (
    rule_id bigint NOT NULL,
    rule_type character varying(20) NOT NULL,
    item_seq character varying(20) NOT NULL,
    ingr_name character varying(200),
    mixture_item_seq character varying(20),
    mixture_item_name character varying(300),
    mixture_ingr_name character varying(200),
    content text,
    etc_otc character varying(10),
    raw_json jsonb,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ck_dur_rule_type CHECK (((rule_type)::text = ANY ((ARRAY['병용금기'::character varying, '임부금기'::character varying, '연령금기'::character varying, '노인주의'::character varying, '서방정분할'::character varying, '효능군중복'::character varying, '용량주의'::character varying, '투여기간주의'::character varying])::text[])))
);


--
-- Name: TABLE dur_rule; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.dur_rule IS 'DUR 규칙';


--
-- Name: COLUMN dur_rule.rule_id; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.dur_rule.rule_id IS '규칙ID';


--
-- Name: COLUMN dur_rule.rule_type; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.dur_rule.rule_type IS '규칙유형';


--
-- Name: COLUMN dur_rule.item_seq; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.dur_rule.item_seq IS '대상품목기준코드';


--
-- Name: COLUMN dur_rule.ingr_name; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.dur_rule.ingr_name IS '대상성분명';


--
-- Name: COLUMN dur_rule.mixture_item_seq; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.dur_rule.mixture_item_seq IS '병용상대품목기준코드 (전문의약품일 수 있어 FK 없음)';


--
-- Name: COLUMN dur_rule.mixture_item_name; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.dur_rule.mixture_item_name IS '병용상대제품명';


--
-- Name: COLUMN dur_rule.mixture_ingr_name; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.dur_rule.mixture_ingr_name IS '병용상대성분명';


--
-- Name: COLUMN dur_rule.content; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.dur_rule.content IS '금기내용';


--
-- Name: COLUMN dur_rule.etc_otc; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.dur_rule.etc_otc IS '전문일반구분';


--
-- Name: COLUMN dur_rule.raw_json; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.dur_rule.raw_json IS '응답원본';


--
-- Name: COLUMN dur_rule.updated_at; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.dur_rule.updated_at IS '수정일시';


--
-- Name: dur_rule_rule_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.dur_rule_rule_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: dur_rule_rule_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.dur_rule_rule_id_seq OWNED BY public.dur_rule.rule_id;


--
-- Name: eval_question; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.eval_question (
    question_id integer NOT NULL,
    question text NOT NULL,
    q_type character varying(20) NOT NULL,
    answer_item_seq character varying(20),
    answer_section character varying(20),
    should_block boolean DEFAULT false NOT NULL,
    expected_warning character varying(10),
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ck_eval_question_type CHECK (((q_type)::text = ANY ((ARRAY['약정보'::character varying, '함께먹기'::character varying, '증상'::character varying, '위험'::character varying, '데이터밖'::character varying, '우회'::character varying])::text[]))),
    CONSTRAINT ck_eval_question_warning CHECK (((expected_warning)::text = ANY ((ARRAY['금기'::character varying, '중복'::character varying, '없음'::character varying])::text[])))
);


--
-- Name: TABLE eval_question; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.eval_question IS '평가 질문';


--
-- Name: COLUMN eval_question.question_id; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.eval_question.question_id IS '평가질문ID';


--
-- Name: COLUMN eval_question.question; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.eval_question.question IS '질문';


--
-- Name: COLUMN eval_question.q_type; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.eval_question.q_type IS '유형';


--
-- Name: COLUMN eval_question.answer_item_seq; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.eval_question.answer_item_seq IS '정답품목기준코드';


--
-- Name: COLUMN eval_question.answer_section; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.eval_question.answer_section IS '정답항목';


--
-- Name: COLUMN eval_question.should_block; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.eval_question.should_block IS '차단대상여부';


--
-- Name: COLUMN eval_question.expected_warning; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.eval_question.expected_warning IS '기대경고 (금기/중복/없음)';


--
-- Name: COLUMN eval_question.created_at; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.eval_question.created_at IS '등록일시';


--
-- Name: eval_question_question_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.eval_question_question_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: eval_question_question_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.eval_question_question_id_seq OWNED BY public.eval_question.question_id;


--
-- Name: eval_result; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.eval_result (
    result_id bigint NOT NULL,
    run_id integer NOT NULL,
    question_id integer NOT NULL,
    answer text,
    retrieved jsonb,
    hit_at_3 boolean,
    source_correct boolean,
    blocked boolean,
    warning_result character varying(10),
    response_ms integer
);


--
-- Name: TABLE eval_result; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.eval_result IS '평가 결과';


--
-- Name: COLUMN eval_result.result_id; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.eval_result.result_id IS '결과ID';


--
-- Name: COLUMN eval_result.run_id; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.eval_result.run_id IS '실행ID';


--
-- Name: COLUMN eval_result.question_id; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.eval_result.question_id IS '평가질문ID';


--
-- Name: COLUMN eval_result.answer; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.eval_result.answer IS '답변';


--
-- Name: COLUMN eval_result.retrieved; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.eval_result.retrieved IS '검색결과 (상위 3개)';


--
-- Name: COLUMN eval_result.hit_at_3; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.eval_result.hit_at_3 IS '적중여부';


--
-- Name: COLUMN eval_result.source_correct; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.eval_result.source_correct IS '출처정답여부';


--
-- Name: COLUMN eval_result.blocked; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.eval_result.blocked IS '차단여부';


--
-- Name: COLUMN eval_result.warning_result; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.eval_result.warning_result IS '경고판정결과';


--
-- Name: COLUMN eval_result.response_ms; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.eval_result.response_ms IS '응답시간(ms)';


--
-- Name: eval_result_result_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.eval_result_result_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: eval_result_result_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.eval_result_result_id_seq OWNED BY public.eval_result.result_id;


--
-- Name: eval_run; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.eval_run (
    run_id integer NOT NULL,
    model character varying(100) NOT NULL,
    prompt_version character varying(20) NOT NULL,
    started_at timestamp with time zone DEFAULT now() NOT NULL,
    finished_at timestamp with time zone,
    hit_at_3_rate numeric(5,2),
    source_accuracy numeric(5,2),
    block_rate numeric(5,2),
    false_block_rate numeric(5,2),
    interaction_accuracy numeric(5,2),
    avg_response_ms integer,
    memo text
);


--
-- Name: TABLE eval_run; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.eval_run IS '평가 실행';


--
-- Name: COLUMN eval_run.run_id; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.eval_run.run_id IS '실행ID';


--
-- Name: COLUMN eval_run.model; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.eval_run.model IS '모델';


--
-- Name: COLUMN eval_run.prompt_version; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.eval_run.prompt_version IS '프롬프트버전';


--
-- Name: COLUMN eval_run.started_at; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.eval_run.started_at IS '시작일시';


--
-- Name: COLUMN eval_run.finished_at; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.eval_run.finished_at IS '종료일시';


--
-- Name: COLUMN eval_run.hit_at_3_rate; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.eval_run.hit_at_3_rate IS '검색적중률(%)';


--
-- Name: COLUMN eval_run.source_accuracy; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.eval_run.source_accuracy IS '출처정확도(%)';


--
-- Name: COLUMN eval_run.block_rate; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.eval_run.block_rate IS '위험질문차단율(%)';


--
-- Name: COLUMN eval_run.false_block_rate; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.eval_run.false_block_rate IS '오차단율(%)';


--
-- Name: COLUMN eval_run.interaction_accuracy; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.eval_run.interaction_accuracy IS '함께먹기정확도(%)';


--
-- Name: COLUMN eval_run.avg_response_ms; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.eval_run.avg_response_ms IS '평균응답시간(ms)';


--
-- Name: COLUMN eval_run.memo; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.eval_run.memo IS '메모';


--
-- Name: eval_run_run_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.eval_run_run_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: eval_run_run_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.eval_run_run_id_seq OWNED BY public.eval_run.run_id;


--
-- Name: ingredient; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.ingredient (
    ingr_id integer NOT NULL,
    ingr_code character varying(20),
    ingr_name character varying(200) NOT NULL
);


--
-- Name: TABLE ingredient; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.ingredient IS '성분';


--
-- Name: COLUMN ingredient.ingr_id; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.ingredient.ingr_id IS '성분ID';


--
-- Name: COLUMN ingredient.ingr_code; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.ingredient.ingr_code IS '성분코드 (DUR, 없을 수 있음)';


--
-- Name: COLUMN ingredient.ingr_name; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.ingredient.ingr_name IS '성분명';


--
-- Name: ingredient_ingr_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.ingredient_ingr_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: ingredient_ingr_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.ingredient_ingr_id_seq OWNED BY public.ingredient.ingr_id;


--
-- Name: notice_text; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.notice_text (
    code character varying(30) NOT NULL,
    text text NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: TABLE notice_text; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.notice_text IS '고정 안내 문구';


--
-- Name: COLUMN notice_text.code; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.notice_text.code IS '문구코드 (DISCLAIMER, EMERGENCY, NO_INFO 등)';


--
-- Name: COLUMN notice_text.text; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.notice_text.text IS '문구';


--
-- Name: COLUMN notice_text.updated_at; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.notice_text.updated_at IS '수정일시';


--
-- Name: pharmacy; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.pharmacy (
    hpid character varying(20) NOT NULL,
    name character varying(200) NOT NULL,
    addr character varying(300),
    tel character varying(30),
    sido character varying(30),
    sigungu character varying(30),
    lat numeric(10,7),
    lon numeric(10,7),
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: TABLE pharmacy; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.pharmacy IS '약국';


--
-- Name: COLUMN pharmacy.hpid; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.pharmacy.hpid IS '기관ID';


--
-- Name: COLUMN pharmacy.name; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.pharmacy.name IS '약국명';


--
-- Name: COLUMN pharmacy.addr; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.pharmacy.addr IS '주소';


--
-- Name: COLUMN pharmacy.tel; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.pharmacy.tel IS '전화번호';


--
-- Name: COLUMN pharmacy.sido; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.pharmacy.sido IS '시도';


--
-- Name: COLUMN pharmacy.sigungu; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.pharmacy.sigungu IS '시군구';


--
-- Name: COLUMN pharmacy.lat; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.pharmacy.lat IS '위도';


--
-- Name: COLUMN pharmacy.lon; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.pharmacy.lon IS '경도';


--
-- Name: COLUMN pharmacy.updated_at; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.pharmacy.updated_at IS '수정일시';


--
-- Name: pharmacy_hours; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.pharmacy_hours (
    hpid character varying(20) NOT NULL,
    day_no smallint NOT NULL,
    open_time character(4),
    close_time character(4),
    CONSTRAINT ck_pharmacy_hours_day CHECK (((day_no >= 1) AND (day_no <= 8)))
);


--
-- Name: TABLE pharmacy_hours; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.pharmacy_hours IS '약국 영업시간';


--
-- Name: COLUMN pharmacy_hours.hpid; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.pharmacy_hours.hpid IS '기관ID';


--
-- Name: COLUMN pharmacy_hours.day_no; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.pharmacy_hours.day_no IS '요일번호 (1=월 ~ 7=일, 8=공휴일)';


--
-- Name: COLUMN pharmacy_hours.open_time; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.pharmacy_hours.open_time IS '여는시각 (HHMM)';


--
-- Name: COLUMN pharmacy_hours.close_time; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.pharmacy_hours.close_time IS '닫는시각 (HHMM, 2400 넘으면 다음날)';


--
-- Name: symptom_keyword; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.symptom_keyword (
    keyword_id integer NOT NULL,
    keyword character varying(100) NOT NULL,
    category character varying(50),
    action character varying(20) DEFAULT '119'::character varying NOT NULL,
    is_active boolean DEFAULT true NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ck_symptom_keyword_action CHECK (((action)::text = ANY ((ARRAY['119'::character varying, '응급실'::character varying, '병원'::character varying])::text[])))
);


--
-- Name: TABLE symptom_keyword; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.symptom_keyword IS '위험 증상 사전';


--
-- Name: COLUMN symptom_keyword.keyword_id; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.symptom_keyword.keyword_id IS '키워드ID';


--
-- Name: COLUMN symptom_keyword.keyword; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.symptom_keyword.keyword IS '표현';


--
-- Name: COLUMN symptom_keyword.category; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.symptom_keyword.category IS '분류 (흉통, 호흡곤란 등)';


--
-- Name: COLUMN symptom_keyword.action; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.symptom_keyword.action IS '안내 (119/응급실/병원)';


--
-- Name: COLUMN symptom_keyword.is_active; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.symptom_keyword.is_active IS '사용여부';


--
-- Name: COLUMN symptom_keyword.created_at; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.symptom_keyword.created_at IS '등록일시';


--
-- Name: symptom_keyword_keyword_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.symptom_keyword_keyword_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: symptom_keyword_keyword_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.symptom_keyword_keyword_id_seq OWNED BY public.symptom_keyword.keyword_id;


--
-- Name: sync_log; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.sync_log (
    sync_id bigint NOT NULL,
    api_name character varying(30) NOT NULL,
    started_at timestamp with time zone DEFAULT now() NOT NULL,
    finished_at timestamp with time zone,
    total_count integer,
    changed_count integer,
    call_count integer,
    status character varying(10) DEFAULT 'running'::character varying NOT NULL,
    error_message text,
    CONSTRAINT ck_sync_log_status CHECK (((status)::text = ANY ((ARRAY['running'::character varying, 'success'::character varying, 'fail'::character varying])::text[])))
);


--
-- Name: TABLE sync_log; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.sync_log IS '수집 기록';


--
-- Name: COLUMN sync_log.sync_id; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.sync_log.sync_id IS '수집ID';


--
-- Name: COLUMN sync_log.api_name; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.sync_log.api_name IS 'API이름';


--
-- Name: COLUMN sync_log.started_at; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.sync_log.started_at IS '시작일시';


--
-- Name: COLUMN sync_log.finished_at; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.sync_log.finished_at IS '종료일시';


--
-- Name: COLUMN sync_log.total_count; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.sync_log.total_count IS '전체건수';


--
-- Name: COLUMN sync_log.changed_count; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.sync_log.changed_count IS '변경건수';


--
-- Name: COLUMN sync_log.call_count; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.sync_log.call_count IS 'API호출수';


--
-- Name: COLUMN sync_log.status; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.sync_log.status IS '상태';


--
-- Name: COLUMN sync_log.error_message; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.sync_log.error_message IS '오류내용';


--
-- Name: sync_log_sync_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.sync_log_sync_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: sync_log_sync_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.sync_log_sync_id_seq OWNED BY public.sync_log.sync_id;


--
-- Name: synonym; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.synonym (
    synonym_id integer NOT NULL,
    word character varying(100) NOT NULL,
    standard character varying(100) NOT NULL,
    syn_type character varying(20) NOT NULL,
    CONSTRAINT ck_synonym_type CHECK (((syn_type)::text = ANY ((ARRAY['제품명_성분'::character varying, '일상_공식'::character varying])::text[])))
);


--
-- Name: TABLE synonym; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.synonym IS '동의어 사전';


--
-- Name: COLUMN synonym.synonym_id; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.synonym.synonym_id IS '동의어ID';


--
-- Name: COLUMN synonym.word; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.synonym.word IS '단어';


--
-- Name: COLUMN synonym.standard; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.synonym.standard IS '표준어';


--
-- Name: COLUMN synonym.syn_type; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.synonym.syn_type IS '종류';


--
-- Name: synonym_synonym_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.synonym_synonym_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: synonym_synonym_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.synonym_synonym_id_seq OWNED BY public.synonym.synonym_id;


--
-- Name: user_med; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.user_med (
    med_id bigint NOT NULL,
    user_id bigint,
    session_id character varying(64),
    item_seq character varying(20) NOT NULL,
    added_by character varying(10) DEFAULT '검색'::character varying NOT NULL,
    seen_update_de date,
    added_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ck_user_med_added_by CHECK (((added_by)::text = ANY ((ARRAY['검색'::character varying, '사진'::character varying])::text[]))),
    CONSTRAINT ck_user_med_owner CHECK (((user_id IS NOT NULL) OR (session_id IS NOT NULL)))
);


--
-- Name: TABLE user_med; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.user_med IS '내 약 목록';


--
-- Name: COLUMN user_med.med_id; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.user_med.med_id IS '내약ID';


--
-- Name: COLUMN user_med.user_id; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.user_med.user_id IS '사용자ID (로그인 후)';


--
-- Name: COLUMN user_med.session_id; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.user_med.session_id IS '세션ID (로그인 전)';


--
-- Name: COLUMN user_med.item_seq; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.user_med.item_seq IS '품목기준코드';


--
-- Name: COLUMN user_med.added_by; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.user_med.added_by IS '등록방법 (검색/사진)';


--
-- Name: COLUMN user_med.seen_update_de; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.user_med.seen_update_de IS '확인한갱신일 (변경 알림용)';


--
-- Name: COLUMN user_med.added_at; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.user_med.added_at IS '등록일시';


--
-- Name: user_med_med_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.user_med_med_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: user_med_med_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.user_med_med_id_seq OWNED BY public.user_med.med_id;


--
-- Name: user_profile; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.user_profile (
    user_id bigint NOT NULL,
    target character varying(10) NOT NULL,
    child_age smallint,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ck_user_profile_target CHECK (((target)::text = ANY ((ARRAY['없음'::character varying, '임부'::character varying, '수유'::character varying, '소아'::character varying, '노인'::character varying])::text[])))
);


--
-- Name: TABLE user_profile; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.user_profile IS '사용자 프로필';


--
-- Name: COLUMN user_profile.user_id; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.user_profile.user_id IS '사용자ID';


--
-- Name: COLUMN user_profile.target; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.user_profile.target IS '대상';


--
-- Name: COLUMN user_profile.child_age; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.user_profile.child_age IS '소아나이 (대상이 소아일 때)';


--
-- Name: COLUMN user_profile.updated_at; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.user_profile.updated_at IS '수정일시';


--
-- Name: app_user user_id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.app_user ALTER COLUMN user_id SET DEFAULT nextval('public.app_user_user_id_seq'::regclass);


--
-- Name: caution_keyword keyword_id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.caution_keyword ALTER COLUMN keyword_id SET DEFAULT nextval('public.caution_keyword_keyword_id_seq'::regclass);


--
-- Name: chat_log log_id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.chat_log ALTER COLUMN log_id SET DEFAULT nextval('public.chat_log_log_id_seq'::regclass);


--
-- Name: drug_chunk chunk_id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.drug_chunk ALTER COLUMN chunk_id SET DEFAULT nextval('public.drug_chunk_chunk_id_seq'::regclass);


--
-- Name: dur_rule rule_id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.dur_rule ALTER COLUMN rule_id SET DEFAULT nextval('public.dur_rule_rule_id_seq'::regclass);


--
-- Name: eval_question question_id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.eval_question ALTER COLUMN question_id SET DEFAULT nextval('public.eval_question_question_id_seq'::regclass);


--
-- Name: eval_result result_id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.eval_result ALTER COLUMN result_id SET DEFAULT nextval('public.eval_result_result_id_seq'::regclass);


--
-- Name: eval_run run_id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.eval_run ALTER COLUMN run_id SET DEFAULT nextval('public.eval_run_run_id_seq'::regclass);


--
-- Name: ingredient ingr_id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ingredient ALTER COLUMN ingr_id SET DEFAULT nextval('public.ingredient_ingr_id_seq'::regclass);


--
-- Name: symptom_keyword keyword_id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.symptom_keyword ALTER COLUMN keyword_id SET DEFAULT nextval('public.symptom_keyword_keyword_id_seq'::regclass);


--
-- Name: sync_log sync_id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sync_log ALTER COLUMN sync_id SET DEFAULT nextval('public.sync_log_sync_id_seq'::regclass);


--
-- Name: synonym synonym_id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.synonym ALTER COLUMN synonym_id SET DEFAULT nextval('public.synonym_synonym_id_seq'::regclass);


--
-- Name: user_med med_id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_med ALTER COLUMN med_id SET DEFAULT nextval('public.user_med_med_id_seq'::regclass);


--
-- Name: app_user pk_app_user; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.app_user
    ADD CONSTRAINT pk_app_user PRIMARY KEY (user_id);


--
-- Name: caution_keyword pk_caution_keyword; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.caution_keyword
    ADD CONSTRAINT pk_caution_keyword PRIMARY KEY (keyword_id);


--
-- Name: chat_log pk_chat_log; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.chat_log
    ADD CONSTRAINT pk_chat_log PRIMARY KEY (log_id);


--
-- Name: drug pk_drug; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.drug
    ADD CONSTRAINT pk_drug PRIMARY KEY (item_seq);


--
-- Name: drug_chunk pk_drug_chunk; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.drug_chunk
    ADD CONSTRAINT pk_drug_chunk PRIMARY KEY (chunk_id);


--
-- Name: drug_ingredient pk_drug_ingredient; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.drug_ingredient
    ADD CONSTRAINT pk_drug_ingredient PRIMARY KEY (item_seq, ingr_id);


--
-- Name: dur_rule pk_dur_rule; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.dur_rule
    ADD CONSTRAINT pk_dur_rule PRIMARY KEY (rule_id);


--
-- Name: eval_question pk_eval_question; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.eval_question
    ADD CONSTRAINT pk_eval_question PRIMARY KEY (question_id);


--
-- Name: eval_result pk_eval_result; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.eval_result
    ADD CONSTRAINT pk_eval_result PRIMARY KEY (result_id);


--
-- Name: eval_run pk_eval_run; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.eval_run
    ADD CONSTRAINT pk_eval_run PRIMARY KEY (run_id);


--
-- Name: ingredient pk_ingredient; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ingredient
    ADD CONSTRAINT pk_ingredient PRIMARY KEY (ingr_id);


--
-- Name: notice_text pk_notice_text; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.notice_text
    ADD CONSTRAINT pk_notice_text PRIMARY KEY (code);


--
-- Name: pharmacy pk_pharmacy; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pharmacy
    ADD CONSTRAINT pk_pharmacy PRIMARY KEY (hpid);


--
-- Name: pharmacy_hours pk_pharmacy_hours; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pharmacy_hours
    ADD CONSTRAINT pk_pharmacy_hours PRIMARY KEY (hpid, day_no);


--
-- Name: symptom_keyword pk_symptom_keyword; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.symptom_keyword
    ADD CONSTRAINT pk_symptom_keyword PRIMARY KEY (keyword_id);


--
-- Name: sync_log pk_sync_log; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sync_log
    ADD CONSTRAINT pk_sync_log PRIMARY KEY (sync_id);


--
-- Name: synonym pk_synonym; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.synonym
    ADD CONSTRAINT pk_synonym PRIMARY KEY (synonym_id);


--
-- Name: user_med pk_user_med; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_med
    ADD CONSTRAINT pk_user_med PRIMARY KEY (med_id);


--
-- Name: user_profile pk_user_profile; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_profile
    ADD CONSTRAINT pk_user_profile PRIMARY KEY (user_id);


--
-- Name: app_user uq_app_user_login; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.app_user
    ADD CONSTRAINT uq_app_user_login UNIQUE (login_id);


--
-- Name: caution_keyword uq_caution_keyword; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.caution_keyword
    ADD CONSTRAINT uq_caution_keyword UNIQUE (keyword);


--
-- Name: drug_chunk uq_drug_chunk_item_section; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.drug_chunk
    ADD CONSTRAINT uq_drug_chunk_item_section UNIQUE (item_seq, section);


--
-- Name: eval_result uq_eval_result; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.eval_result
    ADD CONSTRAINT uq_eval_result UNIQUE (run_id, question_id);


--
-- Name: ingredient uq_ingredient_code; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ingredient
    ADD CONSTRAINT uq_ingredient_code UNIQUE (ingr_code);


--
-- Name: ingredient uq_ingredient_name; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ingredient
    ADD CONSTRAINT uq_ingredient_name UNIQUE (ingr_name);


--
-- Name: symptom_keyword uq_symptom_keyword; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.symptom_keyword
    ADD CONSTRAINT uq_symptom_keyword UNIQUE (keyword);


--
-- Name: synonym uq_synonym; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.synonym
    ADD CONSTRAINT uq_synonym UNIQUE (word, standard);


--
-- Name: ix_chat_log_blocked; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_chat_log_blocked ON public.chat_log USING btree (blocked) WHERE blocked;


--
-- Name: ix_chat_log_created; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_chat_log_created ON public.chat_log USING btree (created_at);


--
-- Name: ix_drug_chunk_embedding; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_drug_chunk_embedding ON public.drug_chunk USING hnsw (embedding public.vector_cosine_ops);


--
-- Name: ix_drug_efcy_trgm; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_drug_efcy_trgm ON public.drug USING gin (efcy public.gin_trgm_ops);


--
-- Name: ix_drug_entp_name_trgm; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_drug_entp_name_trgm ON public.drug USING gin (entp_name public.gin_trgm_ops);


--
-- Name: ix_drug_ingredient_ingr; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_drug_ingredient_ingr ON public.drug_ingredient USING btree (ingr_id);


--
-- Name: ix_drug_item_name_trgm; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_drug_item_name_trgm ON public.drug USING gin (item_name public.gin_trgm_ops);


--
-- Name: ix_dur_rule_item; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_dur_rule_item ON public.dur_rule USING btree (item_seq, rule_type);


--
-- Name: ix_dur_rule_mixture; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_dur_rule_mixture ON public.dur_rule USING btree (mixture_item_seq);


--
-- Name: ix_pharmacy_region; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_pharmacy_region ON public.pharmacy USING btree (sido, sigungu);


--
-- Name: uq_user_med_session; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uq_user_med_session ON public.user_med USING btree (session_id, item_seq) WHERE (session_id IS NOT NULL);


--
-- Name: uq_user_med_user; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uq_user_med_user ON public.user_med USING btree (user_id, item_seq) WHERE (user_id IS NOT NULL);


--
-- Name: chat_log fk_chat_log_drug; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.chat_log
    ADD CONSTRAINT fk_chat_log_drug FOREIGN KEY (target_item_seq) REFERENCES public.drug(item_seq) ON DELETE SET NULL;


--
-- Name: chat_log fk_chat_log_user; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.chat_log
    ADD CONSTRAINT fk_chat_log_user FOREIGN KEY (user_id) REFERENCES public.app_user(user_id) ON DELETE SET NULL;


--
-- Name: drug_chunk fk_drug_chunk_drug; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.drug_chunk
    ADD CONSTRAINT fk_drug_chunk_drug FOREIGN KEY (item_seq) REFERENCES public.drug(item_seq) ON DELETE CASCADE;


--
-- Name: drug_ingredient fk_drug_ingredient_drug; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.drug_ingredient
    ADD CONSTRAINT fk_drug_ingredient_drug FOREIGN KEY (item_seq) REFERENCES public.drug(item_seq) ON DELETE CASCADE;


--
-- Name: drug_ingredient fk_drug_ingredient_ingr; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.drug_ingredient
    ADD CONSTRAINT fk_drug_ingredient_ingr FOREIGN KEY (ingr_id) REFERENCES public.ingredient(ingr_id);


--
-- Name: dur_rule fk_dur_rule_drug; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.dur_rule
    ADD CONSTRAINT fk_dur_rule_drug FOREIGN KEY (item_seq) REFERENCES public.drug(item_seq) ON DELETE CASCADE;


--
-- Name: eval_question fk_eval_question_drug; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.eval_question
    ADD CONSTRAINT fk_eval_question_drug FOREIGN KEY (answer_item_seq) REFERENCES public.drug(item_seq);


--
-- Name: eval_result fk_eval_result_question; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.eval_result
    ADD CONSTRAINT fk_eval_result_question FOREIGN KEY (question_id) REFERENCES public.eval_question(question_id) ON DELETE CASCADE;


--
-- Name: eval_result fk_eval_result_run; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.eval_result
    ADD CONSTRAINT fk_eval_result_run FOREIGN KEY (run_id) REFERENCES public.eval_run(run_id) ON DELETE CASCADE;


--
-- Name: pharmacy_hours fk_pharmacy_hours_pharmacy; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pharmacy_hours
    ADD CONSTRAINT fk_pharmacy_hours_pharmacy FOREIGN KEY (hpid) REFERENCES public.pharmacy(hpid) ON DELETE CASCADE;


--
-- Name: user_med fk_user_med_drug; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_med
    ADD CONSTRAINT fk_user_med_drug FOREIGN KEY (item_seq) REFERENCES public.drug(item_seq);


--
-- Name: user_med fk_user_med_user; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_med
    ADD CONSTRAINT fk_user_med_user FOREIGN KEY (user_id) REFERENCES public.app_user(user_id) ON DELETE CASCADE;


--
-- Name: user_profile fk_user_profile_user; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_profile
    ADD CONSTRAINT fk_user_profile_user FOREIGN KEY (user_id) REFERENCES public.app_user(user_id) ON DELETE CASCADE;


--
-- PostgreSQL database dump complete
--

\unrestrict oB4tLuDd6y37wTo8gNbJuXfNXp5tDs2NQwZopaBLos3RJukh4j6y2oChUlPLYhE

