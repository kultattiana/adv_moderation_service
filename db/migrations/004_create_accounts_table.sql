CREATE TABLE IF NOT EXISTS accounts (
    id SERIAL PRIMARY KEY,
    seller_id INTEGER NOT NULL REFERENCES sellers(seller_id) ON DELETE CASCADE,
    login TEXT NOT NULL,
    password TEXT NOT NULL,
    is_blocked BOOLEAN DEFAULT FALSE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_accounts_login ON accounts(login);
CREATE INDEX IF NOT EXISTS idx_accounts_password ON accounts(password);
CREATE INDEX IF NOT EXISTS idx_accounts_is_blocked ON accounts(is_blocked);