ALTER TABLE students
    ADD COLUMN IF NOT EXISTS payment_start_month DATE,
    ADD COLUMN IF NOT EXISTS last_payment_date DATE;
