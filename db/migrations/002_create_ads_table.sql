CREATE TABLE IF NOT EXISTS ads (
    item_id SERIAL PRIMARY KEY,
    seller_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    category INTEGER NOT NULL CHECK (category >= 0 AND category <= 100),
    images_qty INTEGER DEFAULT 0 CHECK (images_qty >= 0 AND images_qty <= 10),
    is_closed BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (seller_id) REFERENCES sellers(seller_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_ads_seller_id ON ads(seller_id);
CREATE INDEX IF NOT EXISTS idx_ads_category ON ads(category);
CREATE INDEX IF NOT EXISTS idx_ads_created_at ON ads(created_at DESC);