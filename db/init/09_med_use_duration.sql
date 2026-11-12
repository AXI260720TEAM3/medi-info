ALTER TABLE public.med_use_history
ADD COLUMN IF NOT EXISTS duration_days INTEGER
    CONSTRAINT ck_med_use_duration
    CHECK (duration_days >= 1);