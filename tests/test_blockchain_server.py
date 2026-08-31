
from backend.blockchain_api_server import app


def test_login_route_uses_auth_service():
    client = app.test_client()
    client.environ_base['REMOTE_ADDR'] = '198.51.100.11'
    from backend.auth import AuthService
    imported = AuthService()
    imported.register_user('demo', 'secret', 'beekeeper')
    from backend import blockchain_api_server
    blockchain_api_server.AUTH_SERVICE = imported
    response = client.post('/api/login', json={'username': 'demo', 'password': 'secret'})
    assert response.status_code == 200
    assert response.get_json()['success'] is True


def test_batch_creation_requires_authentication_and_owner_tracking():
    client = app.test_client()
    client.environ_base['REMOTE_ADDR'] = '198.51.100.12'
    from backend.auth import AuthService
    service = AuthService()
    service.register_user('beekeeper', 'password1', 'beekeeper')
    from backend import blockchain_api_server
    blockchain_api_server.AUTH_SERVICE = service
    blockchain_api_server.DB_BACKEND = __import__('database.sqlite_store', fromlist=['MockERPBackend']).MockERPBackend(':memory:')

    unauthenticated = client.post('/api/batches', json={'batch_id': 'B-OWNER', 'origin': 'north'})
    assert unauthenticated.status_code == 401

    login = client.post('/api/login', json={'username': 'beekeeper', 'password': 'password1'})
    assert login.status_code == 200
    created = client.post('/api/batches', json={'batch_id': 'B-OWNER', 'origin': 'north'})
    assert created.status_code == 201
    assert blockchain_api_server.DB_BACKEND.get_batch(batch_id='B-OWNER')['owner'] == 'beekeeper'
