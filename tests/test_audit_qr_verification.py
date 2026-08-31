"""Regression tests covering the hardened QR verification flow."""

import urllib.parse

import pytest

from backend.verification_api import VerificationAPI
from database.sqlite_store import MockERPBackend
from qr_service.generator import QRCodeGenerator


def test_qr_generator_uses_https_and_signs_payload():
    generator = QRCodeGenerator(verification_url='https://example.test/verify')
    qr = generator.generate('B-12345')
    parsed = urllib.parse.urlparse(qr)
    params = urllib.parse.parse_qs(parsed.query)

    assert parsed.scheme == 'https'
    assert parsed.netloc == 'example.test'
    assert params['batch_id'] == ['B-12345']
    assert 'sig' in params and params['sig'][0]
    assert 'ts' in params and params['ts'][0].isdigit()


def test_qr_generator_requires_https():
    with pytest.raises(ValueError):
        QRCodeGenerator(verification_url='http://example.test/verify')


def test_verification_api_returns_generic_failure_for_unknown_records():
    backend = MockERPBackend(':memory:')
    api = VerificationAPI(backend)

    assert api.verify_batch(batch_id='B-MISSING')['reason'] == 'verification_failed'
    assert api.verify_batch(qr_id='QR-MISSING')['reason'] == 'verification_failed'
    assert api.verify_batch()['reason'] == 'verification_failed'


def test_verification_api_accepts_known_batch_or_qr_id():
    backend = MockERPBackend(':memory:')
    backend.add_batch({'batch_id': 'B-1', 'qr_id': 'QR-1', 'origin': 'north'})
    api = VerificationAPI(backend)

    assert api.verify_batch(batch_id='B-1')['success'] is True
    assert api.verify_batch(qr_id='QR-1')['success'] is True


def test_database_rejects_duplicate_batch_and_qr_ids():
    backend = MockERPBackend(':memory:')
    backend.add_batch({'batch_id': 'B-OK', 'qr_id': 'QR-OK', 'origin': 'north'})

    with pytest.raises(ValueError):
        backend.add_batch({'batch_id': 'B-OK', 'qr_id': 'QR-NEW', 'origin': 'south'})

    with pytest.raises(ValueError):
        backend.add_batch({'batch_id': 'B-NEW', 'qr_id': 'QR-OK', 'origin': 'west'})
