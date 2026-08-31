
import os
import sqlite3
import uuid
from typing import Any, Dict, Optional


DEFAULT_DB_PATH = os.path.join(os.getcwd(), 'data', 'honeychain.sqlite3')


class MockERPBackend:
    """Simple SQLite-backed batch store used as the application source of truth."""

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or os.getenv('HONEYCHAIN_DB_PATH', DEFAULT_DB_PATH)
        os.makedirs(os.path.dirname(self.db_path) or '.', exist_ok=True)
        self._initialize()

    def _connect(self):
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _initialize(self):
        with self._connect() as conn:
            conn.execute(
                '''
                CREATE TABLE IF NOT EXISTS batches (
                    batch_id TEXT PRIMARY KEY,
                    qr_id TEXT UNIQUE,
                    payload TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                '''
            )
            conn.execute('CREATE INDEX IF NOT EXISTS idx_batches_qr_id ON batches(qr_id)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_batches_batch_id ON batches(batch_id)')

    def add_batch(self, payload: Dict[str, Any]) -> str:
        payload = dict(payload)
        batch_id = payload.get('batch_id') or str(uuid.uuid4())
        qr_id = payload.get('qr_id') or str(uuid.uuid4())
        payload['batch_id'] = batch_id
        payload['qr_id'] = qr_id
        with self._connect() as conn:
            conn.execute(
                'INSERT OR REPLACE INTO batches (batch_id, qr_id, payload) VALUES (?, ?, ?)',
                (batch_id, qr_id, repr(payload)),
            )
        return batch_id

    def get_batch(self, batch_id: Optional[str] = None, qr_id: Optional[str] = None):
        if batch_id is None and qr_id is None:
            return None
        with self._connect() as conn:
            if batch_id is not None:
                row = conn.execute('SELECT * FROM batches WHERE batch_id = ?', (batch_id,)).fetchone()
            else:
                row = conn.execute('SELECT * FROM batches WHERE qr_id = ?', (qr_id,)).fetchone()
        if row is None:
            return None
        value = row['payload']
        try:
            return eval(value, {'__builtins__': {}}, {})
        except Exception:
            return {'batch_id': row['batch_id'], 'qr_id': row['qr_id'], 'payload': value}

    def list_batches(self):
        with self._connect() as conn:
            rows = conn.execute('SELECT * FROM batches ORDER BY created_at DESC').fetchall()
        return [self.get_batch(batch_id=row['batch_id']) for row in rows]
