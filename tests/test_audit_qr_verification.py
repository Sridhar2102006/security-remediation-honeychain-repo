"""
QR VERIFICATION & CONSUMER TRUST AUDIT TESTS
Verify that QR codes provide cryptographic proof of blockchain membership
"""
import pytest
from qr_service.generator import QRCodeGenerator
from backend.verification_api import VerificationAPI
from database.sqlite_store import MockERPBackend


def test_qr_code_contains_batch_id_only(tmp_path):
    """Test: What data is encoded in QR?"""
    gen = QRCodeGenerator(verification_url='https://example.com/verify')
    qr_url = gen.generate('B-12345')
    
    # QR only contains batch_id
    assert 'B-12345' in qr_url
    assert '?' in qr_url
    
    # Missing cryptographic signature
    if '&sig=' not in qr_url and '&proof=' not in qr_url:
        pytest.fail("QR code not cryptographically signed - cannot verify authenticity")


def test_qr_code_url_is_predictable(tmp_path):
    """Test: Can attacker predict valid QR URLs?"""
    gen = QRCodeGenerator(verification_url='https://example.com/verify')
    
    qr1 = gen.generate('B-1')
    qr2 = gen.generate('B-2')
    
    # URLs are sequential - easily predictable
    expected = 'https://example.com/verify?batch_id=B-2'
    assert qr2 == expected
    
    # Attacker can forge any batch_id URL
    pytest.fail("QR URLs are predictable - attacker can forge any URL")


def test_qr_verification_does_not_check_blockchain(tmp_path):
    """Test: Does QR verification check if batch exists on blockchain?"""
    backend = MockERPBackend(str(tmp_path / 'qr.sqlite3'))
    api = VerificationAPI(backend)
    
    # Add batch to DB (but not to blockchain)
    backend.add_batch({'batch_id': 'B-FAKE', 'origin': 'forged'})
    
    # Verify batch
    result = api.verify_batch(batch_id='B-FAKE')
    
    assert result['success'] is True
    
    # Problem: No blockchain verification
    # Attacker can add fake batch to DB and verify it
    pytest.fail("QR verification does not verify blockchain membership")


def test_qr_verification_returns_unverified_data(tmp_path):
    """Test: Does QR verification include blockchain proof?"""
    backend = MockERPBackend(str(tmp_path / 'qr2.sqlite3'))
    backend.add_batch({'batch_id': 'B-1', 'origin': 'north', 'quality': 'excellent'})
    
    api = VerificationAPI(backend)
    result = api.verify_batch(batch_id='B-1')
    
    batch_data = result.get('batch', {})
    
    # Missing blockchain proof
    if 'block_hash' not in batch_data and 'merkle_proof' not in batch_data:
        pytest.fail("QR verification returns unverified DB record without blockchain proof")


def test_qr_verification_batch_enumeration():
    """Test: Can attacker enumerate all batch IDs?"""
    backend = MockERPBackend()
    
    # Add multiple batches
    batch_ids = []
    for i in range(10):
        bid = backend.add_batch({'batch_id': f'B-{i:05d}', 'origin': 'farm'})
        batch_ids.append(bid)
    
    # Try to enumerate
    for i in range(0, 100):
        result = backend.get_batch(batch_id=f'B-{i:05d}')
        if result:
            # Enumeration works
            pytest.fail(f"Batch enumeration possible - found B-{i:05d}")


def test_qr_verification_missing_timestamp_validation():
    """Test: Can consumer verify when batch was created?"""
    backend = MockERPBackend()
    
    batch_id = backend.add_batch({'batch_id': 'B-TIMESTAMP', 'origin': 'farm'})
    batch = backend.get_batch(batch_id=batch_id)
    
    # Batch record exists but consumer cannot verify timestamp
    if 'created_at' not in batch and 'timestamp' not in batch:
        pytest.fail("QR verification missing timestamp - cannot verify freshness")


def test_qr_verification_missing_chain_of_custody():
    """Test: Can consumer verify who touched the product?"""
    backend = MockERPBackend()
    
    batch_id = backend.add_batch({
        'batch_id': 'B-CUSTODY',
        'origin': 'beekeeper',
        'status': 'CREATED'
    })
    batch = backend.get_batch(batch_id=batch_id)
    
    # No custody log, no state history
    if 'custody_log' not in batch and 'history' not in batch:
        pytest.skip("No chain-of-custody log - cannot trace batch path")


def test_qr_verification_duplicate_qr_codes():
    """Test: Can same QR be scanned multiple times?"""
    backend = MockERPBackend()
    
    batch_id = backend.add_batch({'batch_id': 'B-DUP', 'qr_id': 'QR-1'})
    
    # Scan same QR twice
    result1 = backend.get_batch(qr_id='QR-1')
    result2 = backend.get_batch(qr_id='QR-1')
    
    # Same result both times - no consumption tracking
    assert result1 == result2
    pytest.skip("QR codes can be scanned unlimited times - no consumption tracking")


def test_qr_verification_missing_expiration():
    """Test: Do QR codes expire?"""
    backend = MockERPBackend()
    
    batch_id = backend.add_batch({'batch_id': 'B-EXPIRE', 'expiration': '2024-01-01'})
    batch = backend.get_batch(batch_id=batch_id)
    
    # Consumer doesn't get expiration info
    if 'expiration' not in batch:
        pytest.skip("QR verification missing product expiration")


def test_qr_verification_can_modify_batch_after_qr_generated(tmp_path):
    """Test: Can batch data be modified after QR is generated?"""
    backend = MockERPBackend(str(tmp_path / 'qr_modify.sqlite3'))
    
    # Create batch
    batch_id = backend.add_batch({
        'batch_id': 'B-MODIFY',
        'origin': 'clean_farm',
        'quality': 'excellent',
        'price': 100
    })
    
    # QR generated and sent to consumer
    qr_url = f'https://example.com/verify?batch_id={batch_id}'
    
    # Attacker modifies batch in DB
    backend.add_batch({
        'batch_id': batch_id,  # Same ID
        'origin': 'toxic_waste',
        'quality': 'contaminated',
        'price': 1  # Price slashed
    })
    
    # Consumer scans QR
    result = backend.get_batch(batch_id=batch_id)
    
    # Consumer gets contaminated batch data!
    assert result['origin'] == 'toxic_waste'
    pytest.fail("Batch data can be modified after QR generated - consumer sees false data")


def test_qr_verification_no_cryptographic_proof():
    """Test: Is there a cryptographic proof of batch creation?"""
    backend = MockERPBackend()
    batch_id = backend.add_batch({'batch_id': 'B-PROOF'})
    batch = backend.get_batch(batch_id=batch_id)
    
    # Missing blockchain hash, Merkle proof, digital signature
    has_proof = any(key in batch for key in ['block_hash', 'merkle_proof', 'signature', 'proof'])
    
    if not has_proof:
        pytest.fail("QR verification provides no cryptographic proof of blockchain membership")


def test_qr_code_injection_via_batch_id(tmp_path):
    """Test: Can attacker inject special chars in batch_id for URL?"""
    gen = QRCodeGenerator(verification_url='https://example.com/verify')
    
    # Inject URL parameter
    qr = gen.generate('B-1&admin=true')
    
    # URL parsing would pick up admin parameter
    # Consumer app should not be vulnerable, but backend should validate
    if '&admin=' in qr:
        pytest.skip("URL injection possible via batch_id")


def test_qr_generation_requires_https():
    """Test: QR code must use HTTPS for verification URL"""
    try:
        gen = QRCodeGenerator(verification_url='http://example.com/verify')
        pytest.fail("QR generator accepted HTTP URL - MitM possible")
    except ValueError:
        # Good - requires HTTPS
        pass


def test_qr_verification_missing_identity_verification():
    """Test: Can consumer verify beekeeper's identity?"""
    backend = MockERPBackend()
    
    batch_id = backend.add_batch({
        'batch_id': 'B-IDENTITY',
        'beekeeper': 'John Smith',
        'origin': 'farm-123'
    })
    batch = backend.get_batch(batch_id=batch_id)
    
    # Name is just a string - not verified
    # Could be forged
    if 'beekeeper_signature' not in batch and 'beekeeper_cert' not in batch:
        pytest.skip("Beekeeper identity not verified - fraud possible")
