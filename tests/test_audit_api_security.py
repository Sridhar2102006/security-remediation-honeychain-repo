"""Regression tests for authentication, request hardening, and duplicate protection."""

import uuid

import pytest

from backend import blockchain_api_server
from backend.auth import AuthService
from backend.blockchain_api_server import app


@pytest.fixture
def client():
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    client = app.test_client()
    client.environ_base['REMOTE_ADDR'] = f'198.51.100.{uuid.uuid4().int % 255}'
    return client


@pytest.fixture
def auth_service():
    service = AuthService()
    service.register_user('beekeeper', 'password1', 'beekeeper')
    service.register_user('distributor', 'password2', 'distributor')
    service.register_user('retailer', 'password3', 'retailer')
    blockchain_api_server.AUTH_SERVICE = service
    blockchain_api_server.DB_BACKEND = __import__('database.sqlite_store', fromlist=['MockERPBackend']).MockERPBackend(':memory:')
    return service


def test_api_batch_creation_requires_authentication(client):
    response = client.post('/api/batches', json={'batch_id': 'B-1', 'origin': 'north'})
    assert response.status_code == 401


def test_api_batch_creation_requires_role_and_tracks_owner(client, auth_service):
    client.post('/api/login', json={'username': 'beekeeper', 'password': 'password1'})
    response = client.post('/api/batches', json={'batch_id': 'B-1', 'origin': 'north'})
    assert response.status_code == 201

    response = client.post('/api/login', json={'username': 'distributor', 'password': 'password2'})
    assert response.status_code == 200
    response = client.post('/api/batches', json={'batch_id': 'B-2', 'origin': 'south'})
    assert response.status_code == 401


def test_api_batch_reading_is_restricted_to_owner(client, auth_service):
    auth_service.register_user('beekeeper2', 'pass', 'beekeeper')
    auth_service.register_user('distributor2', 'pass', 'distributor')

    client.post('/api/login', json={'username': 'beekeeper2', 'password': 'pass'})
    created = client.post('/api/batches', json={'batch_id': 'B-SECRET', 'origin': 'secret-farm'})
    assert created.status_code == 201

    client.post('/api/login', json={'username': 'distributor2', 'password': 'pass'})
    response = client.get('/api/batches/B-SECRET')
    assert response.status_code == 403


def test_api_payload_size_limit_is_enforced(client, auth_service):
    client.post('/api/login', json={'username': 'beekeeper', 'password': 'password1'})
    payload = {'batch_id': 'B-LARGE', 'payload': 'x' * (2 * 1024 * 1024)}
    response = client.post('/api/batches', json=payload)
    assert response.status_code == 413


def test_api_rate_limits_failed_logins(client, auth_service):
    blockchain_api_server.LOGIN_RATE_LIMITER = blockchain_api_server.RateLimiter(2, 60)
    for _ in range(2):
        response = client.post('/api/login', json={'username': 'attacker', 'password': 'wrong'})
        assert response.status_code == 401

    response = client.post('/api/login', json={'username': 'attacker', 'password': 'wrong'})
    assert response.status_code == 429


def test_api_error_messages_are_generic_for_invalid_credentials(client, auth_service):
    bad_pass = client.post('/api/login', json={'username': 'beekeeper', 'password': 'WRONG'}).get_json()
    bad_user = client.post('/api/login', json={'username': 'DOESNOTEXIST', 'password': 'anything'}).get_json()
    assert bad_pass['error'] == 'invalid_credentials'
    assert bad_user['error'] == 'invalid_credentials'


def test_api_duplicate_batch_id_is_rejected(client, auth_service):
    client.post('/api/login', json={'username': 'beekeeper', 'password': 'password1'})
    first = client.post('/api/batches', json={'batch_id': 'B-DUPLICATE', 'origin': 'farm1'})
    second = client.post('/api/batches', json={'batch_id': 'B-DUPLICATE', 'origin': 'farm2'})
    assert first.status_code == 201
    assert second.status_code == 409


def test_api_health_check_is_public(client):
    assert client.get('/healthz').status_code == 200
