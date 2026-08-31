from backend.auth import AuthService
from backend.blockchain_api_server import app
from database.sqlite_store import MockERPBackend


def test_full_demo_flow_login_batch_and_verify_via_qr_id():
    service = AuthService()
    service.register_user('beekeeper', 'demo-pass', 'beekeeper')
    from backend import blockchain_api_server

    blockchain_api_server.AUTH_SERVICE = service
    blockchain_api_server.DB_BACKEND = MockERPBackend(':memory:')

    client = app.test_client()
    client.environ_base['REMOTE_ADDR'] = '203.0.113.9'

    login = client.post('/api/login', json={'username': 'beekeeper', 'password': 'demo-pass'})
    assert login.status_code == 200
    assert login.get_json()['success'] is True

    create = client.post('/api/batches', json={'batch_id': 'B-9001', 'origin': 'north', 'qr_id': 'QR-9001'})
    assert create.status_code == 201
    assert create.get_json()['consensus']['phase'] == 'FINALIZE'
    assert len(blockchain_api_server.DB_BACKEND.list_blocks()) == 1

    verify = client.post('/api/verify', json={'qr_id': 'QR-9001'})
    assert verify.status_code == 200
    assert verify.get_json()['batch_id'] == 'B-9001'

    public_verify = client.get('/verify/QR-9001')
    assert public_verify.status_code == 200
    assert 'B-9001' in public_verify.get_data(as_text=True)

    dashboard = client.get('/dashboard')
    assert dashboard.status_code == 200
    body = dashboard.get_data(as_text=True).lower()
    assert 'honeychain' in body
    assert 'create batch' in body


def test_designation_login_renders_role_specific_workspace():
    service = AuthService()
    service.register_user('kvic_admin', 'admin-pass', 'admin')
    from backend import blockchain_api_server

    blockchain_api_server.AUTH_SERVICE = service
    blockchain_api_server.DB_BACKEND = MockERPBackend(':memory:')
    client = app.test_client()

    login = client.post(
        '/api/login',
        json={'username': 'kvic_admin', 'password': 'admin-pass', 'designation': 'admin'},
    )
    assert login.status_code == 200
    page = client.get('/dashboard')
    body = page.get_data(as_text=True)
    assert 'KVIC / Network Administrator' in body
    assert 'Network oversight' in body
    assert 'Create Batch' not in body
