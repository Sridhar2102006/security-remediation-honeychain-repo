CREATE TABLE IF NOT EXISTS batches (
    batch_id TEXT PRIMARY KEY,
    qr_id TEXT UNIQUE,
    payload TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_batches_qr_id ON batches(qr_id);
CREATE INDEX IF NOT EXISTS idx_batches_batch_id ON batches(batch_id);

CREATE TABLE IF NOT EXISTS blocks (
    block_index INTEGER PRIMARY KEY,
    block_hash TEXT UNIQUE NOT NULL,
    previous_hash TEXT NOT NULL,
    payload JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
