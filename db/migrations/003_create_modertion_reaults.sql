CREATE TABLE IF NOT EXISTS moderation_results (
    id SERIAL PRIMARY KEY,
    item_id INTEGER REFERENCES ads(item_id) ON DELETE CASCADE,
    status VARCHAR(20) NOT NULL,
    is_violation BOOLEAN,
    probability FLOAT CHECK (probability >= 0 AND probability <= 1),
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processed_at TIMESTAMP,

    CONSTRAINT valid_status CHECK (status IN ('pending', 'completed', 'failed'))
);

CREATE INDEX IF NOT EXISTS idx_moderation_results_item_id ON moderation_results(item_id);
CREATE INDEX IF NOT EXISTS idx_moderation_results_status ON moderation_results(status);
CREATE INDEX IF NOT EXISTS idx_moderation_results_is_violation ON moderation_results(is_violation);