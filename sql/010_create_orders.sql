CREATE TABLE IF NOT EXISTS orders (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    plan_id INTEGER NOT NULL,
    plan_name VARCHAR(100) NOT NULL,
    amount_paise INTEGER NOT NULL CHECK (amount_paise > 0),
    currency VARCHAR(3) NOT NULL DEFAULT 'INR' CHECK (currency = 'INR'),
    razorpay_order_id VARCHAR(100) NOT NULL UNIQUE,
    status VARCHAR(10) NOT NULL DEFAULT 'created'
        CHECK (status IN ('created', 'paid', 'failed')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS orders_user_plan_created_idx
    ON orders (user_id, plan_id, created_at DESC)
    WHERE status = 'created';
