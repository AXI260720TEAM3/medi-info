ALTER TABLE public.push_delivery_log
ADD COLUMN IF NOT EXISTS last_attempt_at
    TIMESTAMPTZ NOT NULL DEFAULT now();