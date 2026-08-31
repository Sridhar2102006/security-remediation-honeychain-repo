
from backend.blockchain_api_server import app


def test_login_route_uses_auth_service():
    client = app.test_client()
    from backend.auth import AuthService
    imported = AuthService()
    imported.register_user('demo', 'secret', 'beekeeper')
    from backend import blockchain_api_server
    blockchain_api_server.AUTH_SERVICE = imported
    response = client.post('/api/login', json={'username': 'demo', 'password': 'secret'})
    assert response.status_code == 200
    assert response.get_json()['success'] is True
