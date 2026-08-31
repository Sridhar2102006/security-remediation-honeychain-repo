
import pytest

from database.sqlite_store import MockERPBackend


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
