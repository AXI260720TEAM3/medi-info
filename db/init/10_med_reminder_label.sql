ALTER TABLE public.med_reminder
ADD COLUMN IF NOT EXISTS alarm_label VARCHAR(20)
CHECK (
    alarm_label IN (
        '아침',
        '점심',
        '저녁',
        '취침 전',
        '식전',
        '식후'
    )
);