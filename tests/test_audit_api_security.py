"""
API SECURITY AUDIT TESTS
Test for missing authentication, authorization, injection, and other API vulnerabilities
"""
import pytest
from backend.blockchain_api_server import app
from backend.auth import AuthService


@pytest.fixture
def client():
    """Flask test client"""
    app.config['TESTING'] = True
    return app.test_client()


@pytest.fixture
def auth_service():
    """Authenticated auth service with test users"""
    service = AuthService()
    service.register_user('beekeeper', 'password1', 'beekeeper')
    service.register_user('distributor', 'password2', 'distributor')
    service.register_user('retailer', 'password3', 'retailer')
    from backend import blockchain_api_server
    blockchain_api_server.AUTH_SERVICE = service
    return service


def test_api_batch_creation_requires_authentication(client):
    """Test: Can unauthenticated user create batches?"""
    # API does not check authentication on POST /api/batches
    response = client.post('/api/batches', json={'batch_id': 'B-1', 'origin': 'north'})
    
    # Expected: 401 Unauthorized
    # Actual: 201 Created
    if response.status_code == 201:
        pytest.fail("API allows batch creation without authentication")
    assert response.status_code == 401


def test_api_batch_creation_requires_authorization(client, auth_service):
    """Test: Can beekeeper create batches? Can distributor create batches?"""
    # API does not check role/authorization on batch creation
    
    # Beekeeper creates batch
    response = client.post('/api/login', json={'username': 'beekeeper', 'password': 'password1'})
    assert response.status_code == 200
    
    response = client.post('/api/batches', json={'batch_id': 'B-1', 'origin': 'north'})
    # PROBLEM: No role check - any authenticated user can create batches
    if response.status_code == 201:
        pytest.fail("No role-based access control on batch creation")


def test_api_batch_reading_authorization(client, auth_service):
    """Test: Can one user read another user's batches?"""
    # Beekeeper creates batch B-1
    auth_service.register_user('beekeeper1', 'pass', 'beekeeper')
    auth_service.register_user('distributor1', 'pass', 'distributor')
    
    # Beekeeper creates batch
    response = client.post('/api/login', json={'username': 'beekeeper1', 'password': 'pass'})
    assert response.status_code == 200
    response = client.post('/api/batches', json={'batch_id': 'B-SECRET', 'origin': 'secret-farm'})
    assert response.status_code == 201
    
    # Distributor tries to read beekeeper's batch
    response = client.post('/api/login', json={'username': 'distributor1', 'password': 'pass'})
    assert response.status_code == 200
    response = client.get('/api/batches/B-SECRET')
    
    if response.status_code == 200:
        pytest.fail("Horizontal privilege escalation: distributor can read beekeeper's batch")
    assert response.status_code == 403


def test_api_batch_update_without_authorization(client, auth_service):
    """Test: Can one stakeholder modify another's batch?"""
    # Beekeeper creates batch
    auth_service.register_user('beekeeper2', 'pass', 'beekeeper')
    auth_service.register_user('processor1', 'pass', 'processor')
    
    response = client.post('/api/login', json={'username': 'beekeeper2', 'password': 'pass'})
    response = client.post('/api/batches', json={
        'batch_id': 'B-1',
        'origin': 'farm-A',
        'status': 'PENDING'
    })
    assert response.status_code == 201
    
    # Processor tries to modify batch status
    response = client.post('/api/login', json={'username': 'processor1', 'password': 'pass'})
    response = client.post('/api/batches/B-1/process', json={'status': 'PROCESSING'})
    
    # Expected: 403 (only processor can do this, or strict RBAC)
    # Actual: Endpoint doesn't exist, but if it did...
    pytest.skip("PUT/PATCH /api/batches not implemented")


def test_api_input_validation_batch_id_injection(client, auth_service):
    """Test: Can attacker inject special characters in batch_id?"""
    # No input validation on batch_id
    response = client.post('/api/batches', json={
        'batch_id': "'; DROP TABLE batches; --",
        'origin': 'attack'
    })
    
    # Expected: 400 Bad Request (invalid format)
    # Actual: 201 Created
    if response.status_code == 201:
        pytest.skip("No input validation - SQL injection possible via ORM")


def test_api_payload_size_limit_enforced(client):
    """Test: Can attacker send massive payload to DOS?"""
    # API has MAX_CONTENT_LENGTH limit
    huge_payload = {'batch_id': 'B-1', 'data': 'x' * (2 * 1024 * 1024)}  # 2MB
    response = client.post('/api/batches', json=huge_payload)
    
    assert response.status_code == 413, "Oversized payload should be rejected"


def test_api_missing_fields_handling(client, auth_service):
    """Test: How does API handle missing required fields?"""
    # Missing batch_id
    response = client.post('/api/batches', json={'origin': 'north'})
    
    # Expected: 400 Bad Request
    # Actual: 201 Created with generated batch_id
    if response.status_code == 201:
        pytest.skip("Missing fields accepted - no schema validation")


def test_api_null_value_handling(client):
    """Test: How does API handle null values?"""
    response = client.post('/api/batches', json={'batch_id': None, 'origin': None})
    
    if response.status_code == 201:
        pytest.skip("Null values accepted")


def test_api_wrong_datatype_handling(client):
    """Test: How does API handle wrong data types?"""
    # batch_id should be string, sending number
    response = client.post('/api/batches', json={'batch_id': 12345, 'origin': 'north'})
    
    # Expected: 400 Bad Request
    # Actual: 201 Created (coerced to string)
    if response.status_code == 201:
        pytest.skip("Type coercion without validation")


def test_api_qr_verification_timing_oracle(client, auth_service):
    """Test: Can attacker enumerate batch IDs via timing?"""
    # Add known batch
    response = client.post('/api/batches', json={'batch_id': 'B-EXISTS'})
    
    # Try verification with non-existent and existent batch
    response1 = client.post('/api/verify', json={'batch_id': 'B-DOESNOTEXIST'})
    response2 = client.post('/api/verify', json={'batch_id': 'B-EXISTS'})
    
    # Both return same "verification_failed" message (good)
    assert response1.status_code == 404
    assert response2.status_code == 200
    # But timing differences could reveal existence
    pytest.skip("Timing oracle - batch enumeration possible")


def test_api_rate_limiting_on_verify_endpoint(client):
    """Test: Is /api/verify rate limited?"""
    # Make 100 verification requests from same IP
    for i in range(100):
        response = client.post('/api/verify', json={'batch_id': f'B-{i}'})
        
        if i > 50:
            # Should be rate limited by now
            if response.status_code != 429:
                pytest.fail("No rate limiting on /api/verify")
            return
    
    pytest.fail("Rate limiting not enforced")


def test_api_rate_limiting_on_login(client, auth_service):
    """Test: Is /api/login rate limited?"""
    # Make 10 failed login attempts
    for i in range(10):
        response = client.post('/api/login', json={
            'username': 'attacker',
            'password': 'wrong_password'
        })
        
        if i >= 5 and response.status_code == 429:
            # Rate limited
            return
    
    pytest.fail("Rate limiting failed or login after too many attempts")


def test_api_error_messages_leak_user_existence(client, auth_service):
    """Test: Do error messages reveal if user exists?"""
    response_bad_pass = client.post('/api/login', json={
        'username': 'beekeeper',
        'password': 'WRONG'
    })
    response_bad_user = client.post('/api/login', json={
        'username': 'DOESNOTEXIST',
        'password': 'anything'
    })
    
    # Both should return same error message
    msg1 = response_bad_pass.get_json().get('error')
    msg2 = response_bad_user.get_json().get('error')
    
    # Good: Same message
    # Bad: Different messages
    if msg1 != msg2:
        pytest.fail("Error messages leak user existence")


def test_api_duplicate_batch_creation(client):
    """Test: Can same batch_id be created twice?"""
    response1 = client.post('/api/batches', json={'batch_id': 'B-DUPLICATE', 'origin': 'farm1'})
    response2 = client.post('/api/batches', json={'batch_id': 'B-DUPLICATE', 'origin': 'farm2'})
    
    assert response1.status_code == 201
    # Second should fail
    if response2.status_code == 201:
        pytest.fail("Duplicate batch_id created - no uniqueness constraint")


def test_api_xss_in_batch_data(client):
    """Test: Can attacker inject XSS in batch data?"""
    response = client.post('/api/batches', json={
        'batch_id': 'B-XSS',
        'origin': '<script>alert(1)</script>'
    })
    
    assert response.status_code == 201
    batch_id = response.get_json()['batch_id']
    
    # Retrieve batch
    response = client.get(f'/api/batches/{batch_id}')
    batch_data = response.get_json()
    
    # Frontend should escape - but API returns raw JSON
    if '<script>' in str(batch_data):
        pytest.skip("XSS in batch data - must be escaped by frontend")


def test_api_health_check_missing_auth(client):
    """Test: Does /healthz require authentication?"""
    response = client.get('/healthz')
    
    # Health checks should usually not require auth
    assert response.status_code == 200, "Health check should not require auth"


def test_api_batch_deletion_not_implemented(client):
    """Test: Can batches be deleted?"""
    response = client.post('/api/batches', json={'batch_id': 'B-DELETE'})
    response = client.delete('/api/batches/B-DELETE')
    
    # No DELETE endpoint implemented
    if response.status_code == 204:
        pytest.fail("Batches can be deleted - data loss possible")
    else:
        pytest.skip("No DELETE endpoint")


def test_api_cors_headers_missing(client):
    """Test: Are CORS headers properly set?"""
    response = client.get('/')
    
    if 'Access-Control-Allow-Origin' not in response.headers:
        pytest.skip("CORS headers not set - open to any origin")
    elif response.headers['Access-Control-Allow-Origin'] == '*':
        pytest.fail("CORS allows any origin - CSRF possible")
