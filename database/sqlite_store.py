
import json
import os
import sqlite3
import uuid
from typing import Any, Dict, Optional

try:
    import psycopg
    from psycopg.types.json import Jsonb
except ImportError:  # pragma: no cover - optional runtime dependency
    psycopg = None
    Jsonb = None


DEFAULT_DB_PATH = os.path.join(os.getcwd(), 'data', 'honeychain.sqlite3')


class MockERPBackend:
    """SQLite-first batch store that can also target PostgreSQL via DATABASE_URL."""

    def __init__(self, db_path: Optional[str] = None):
        default_db = os.getenv('DATABASE_URL') or os.getenv('HONEYCHAIN_DB_PATH', DEFAULT_DB_PATH)
        self.db_path = db_path or default_db
        self._is_postgres = bool(self.db_path and self.db_path.startswith(('postgres://', 'postgresql://')))
        self._memory_conn = None
        self._pg_conn = None
        if not self._is_postgres and self.db_path != ':memory:':
            os.makedirs(os.path.dirname(self.db_path) or '.', exist_ok=True)
        self._initialize()

    def _connect(self):
        if self._is_postgres:
            if psycopg is None:
                raise RuntimeError('psycopg is required when DATABASE_URL points at PostgreSQL')
            if self._pg_conn is None:
                self._pg_conn = psycopg.connect(self.db_path, autocommit=False)
            return self._pg_conn
        if self.db_path == ':memory:':
            if self._memory_conn is None:
                self._memory_conn = sqlite3.connect(self.db_path, check_same_thread=False)
                self._memory_conn.row_factory = sqlite3.Row
            return self._memory_conn
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _initialize(self):
        if self._is_postgres:
            with self._connect() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        '''
                        CREATE TABLE IF NOT EXISTS batches (
                            batch_id TEXT PRIMARY KEY,
                            qr_id TEXT UNIQUE,
                            payload JSONB NOT NULL,
                            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                        )
                        '''
                    )
                    cur.execute('CREATE INDEX IF NOT EXISTS idx_batches_qr_id ON batches(qr_id)')
                    cur.execute('CREATE INDEX IF NOT EXISTS idx_batches_batch_id ON batches(batch_id)')
                    cur.execute(
                        '''
                        CREATE TABLE IF NOT EXISTS blocks (
                            block_index INTEGER PRIMARY KEY,
                            block_hash TEXT UNIQUE NOT NULL,
                            previous_hash TEXT NOT NULL,
                            payload JSONB NOT NULL,
                            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                        )
                        '''
                    )
            return

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
            conn.execute(
                '''
                CREATE TABLE IF NOT EXISTS blocks (
                    block_index INTEGER PRIMARY KEY,
                    block_hash TEXT UNIQUE NOT NULL,
                    previous_hash TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                '''
            )

    def add_batch(self, payload: Dict[str, Any]) -> str:
        payload = dict(payload)
        batch_id = payload.get('batch_id') or str(uuid.uuid4())
        qr_id = payload.get('qr_id') or str(uuid.uuid4())
        payload['batch_id'] = batch_id
        payload['qr_id'] = qr_id
        serialized = json.dumps(payload, sort_keys=True)
        try:
            if self._is_postgres:
                with self._connect() as conn:
                    with conn.cursor() as cur:
                        cur.execute(
                            'INSERT INTO batches (batch_id, qr_id, payload) VALUES (%s, %s, %s)',
                            (batch_id, qr_id, Jsonb(json.loads(serialized))),
                        )
                return batch_id
            with self._connect() as conn:
                conn.execute(
                    'INSERT INTO batches (batch_id, qr_id, payload) VALUES (?, ?, ?)',
                    (batch_id, qr_id, serialized),
                )
        except (sqlite3.IntegrityError, Exception) as exc:
            if self._is_postgres and getattr(exc, 'diag', None) and exc.diag.get('constraint_name'):
                raise ValueError('duplicate batch_id or qr_id') from exc
            if not self._is_postgres and isinstance(exc, sqlite3.IntegrityError):
                raise ValueError('duplicate batch_id or qr_id') from exc
            raise
        return batch_id

    def get_batch(self, batch_id: Optional[str] = None, qr_id: Optional[str] = None):
        if batch_id is None and qr_id is None:
            return None
        if self._is_postgres:
            with self._connect() as conn:
                with conn.cursor() as cur:
                    if batch_id is not None:
                        cur.execute('SELECT batch_id, qr_id, payload FROM batches WHERE batch_id = %s', (batch_id,))
                    else:
                        cur.execute('SELECT batch_id, qr_id, payload FROM batches WHERE qr_id = %s', (qr_id,))
                    row = cur.fetchone()
            if row is None:
                return None
            _, _, payload = row
            if isinstance(payload, str):
                try:
                    return json.loads(payload)
                except (TypeError, ValueError):
                    return {'batch_id': row[0], 'qr_id': row[1], 'payload': payload}
            return payload

        with self._connect() as conn:
            if batch_id is not None:
                row = conn.execute('SELECT * FROM batches WHERE batch_id = ?', (batch_id,)).fetchone()
            else:
                row = conn.execute('SELECT * FROM batches WHERE qr_id = ?', (qr_id,)).fetchone()
        if row is None:
            return None
        value = row['payload']
        try:
            return json.loads(value)
        except (TypeError, ValueError):
            return {'batch_id': row['batch_id'], 'qr_id': row['qr_id'], 'payload': value}

    def list_batches(self):
        if self._is_postgres:
            with self._connect() as conn:
                with conn.cursor() as cur:
                    cur.execute('SELECT batch_id FROM batches ORDER BY created_at DESC')
                    rows = cur.fetchall()
            return [self.get_batch(batch_id=row[0]) for row in rows]
        with self._connect() as conn:
            rows = conn.execute('SELECT * FROM batches ORDER BY created_at DESC').fetchall()
        return [self.get_batch(batch_id=row['batch_id']) for row in rows]

    def add_block(self, record: Dict[str, Any]) -> None:
        block = dict(record.get('block') or {})
        block_index = int(block.get('index', 0))
        block_hash = str(record.get('hash', ''))
        previous_hash = str(block.get('previous_hash', '0' * 64))
        if not block_hash:
            raise ValueError('block hash is required')
        serialized = json.dumps(block, sort_keys=True)
        if self._is_postgres:
            with self._connect() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        'INSERT INTO blocks (block_index, block_hash, previous_hash, payload) VALUES (%s, %s, %s, %s)',
                        (block_index, block_hash, previous_hash, Jsonb(json.loads(serialized))),
                    )
            return
        with self._connect() as conn:
            try:
                conn.execute(
                    'INSERT INTO blocks (block_index, block_hash, previous_hash, payload) VALUES (?, ?, ?, ?)',
                    (block_index, block_hash, previous_hash, serialized),
                )
            except sqlite3.IntegrityError as exc:
                raise ValueError('duplicate block index or hash') from exc

    def list_blocks(self):
        if self._is_postgres:
            with self._connect() as conn:
                with conn.cursor() as cur:
                    cur.execute('SELECT block_index, block_hash, previous_hash, payload FROM blocks ORDER BY block_index')
                    rows = cur.fetchall()
            return [
                {
                    'block': payload if isinstance(payload, dict) else json.loads(payload),
                    'hash': block_hash,
                }
                for block_index, block_hash, previous_hash, payload in rows
            ]
        with self._connect() as conn:
            rows = conn.execute(
                'SELECT block_index, block_hash, previous_hash, payload FROM blocks ORDER BY block_index'
            ).fetchall()
        return [
            {'block': json.loads(row['payload']), 'hash': row['block_hash']}
            for row in rows
        ]

    def check_connection(self) -> bool:
        if self._is_postgres:
            with self._connect() as conn:
                with conn.cursor() as cur:
                    cur.execute('SELECT 1')
                    return cur.fetchone()[0] == 1
        with self._connect() as conn:
            return conn.execute('SELECT 1').fetchone()[0] == 1
