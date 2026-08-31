
import pytest

from database.sqlite_store import MockERPBackend


def test_postgres_connection_is_not_reused_after_operation(monkeypatch):
    class FakeCursor:
        def execute(self, *_args):
            return None

        def fetchone(self):
            return (1,)

        def fetchall(self):
            return []

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

    class FakeConnection:
        def __init__(self):
            self.closed = False

        def cursor(self):
            if self.closed:
                raise RuntimeError('closed connection reused')
            return FakeCursor()

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            self.closed = True
            return False

    connections = []

    def connect(*_args, **_kwargs):
        connection = FakeConnection()
        connections.append(connection)
        return connection

    import database.sqlite_store as store_module
    monkeypatch.setattr(store_module.psycopg, 'connect', connect)
    backend = MockERPBackend('postgresql://example/honeychain')
    backend.check_connection()
    backend.check_connection()
    assert len(connections) >= 3
    assert all(connection.closed for connection in connections)


def test_batch_persists_across_restart(tmp_path):
    db_path = tmp_path / 'state.sqlite3'
    first = MockERPBackend(str(db_path))
    batch_id = first.add_batch({'batch_id': 'B-1', 'qr_id': 'QR-1', 'origin': 'north'})
    second = MockERPBackend(str(db_path))
    stored = second.get_batch(batch_id=batch_id)
    assert stored['qr_id'] == 'QR-1'
    assert second.get_batch(qr_id='QR-1')['batch_id'] == batch_id


def test_add_batch_rejects_duplicate_batch_ids(tmp_path):
    backend = MockERPBackend(str(tmp_path / 'dupe.sqlite3'))
    backend.add_batch({'batch_id': 'B-1', 'qr_id': 'QR-1', 'origin': 'north'})
    with pytest.raises(ValueError):
        backend.add_batch({'batch_id': 'B-1', 'qr_id': 'QR-2', 'origin': 'south'})
