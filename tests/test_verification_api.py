
from backend.verification_api import VerificationAPI
from database.sqlite_store import MockERPBackend


def test_verification_returns_generic_failure_for_missing_records(tmp_path):
    backend = MockERPBackend(str(tmp_path / 'verify.sqlite3'))
    api = VerificationAPI(backend)
    result = api.verify_batch(qr_id='missing')
    assert result['success'] is False
    assert result['reason'] == 'verification_failed'
