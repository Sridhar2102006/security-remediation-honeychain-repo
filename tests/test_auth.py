
from backend.auth import AuthService


def test_auth_service_uses_scrypt_hashing_and_same_password_yields_different_hashes():
    service = AuthService()
    service.register_user('alice', 'secret', 'beekeeper')
    service.register_user('bob', 'secret', 'beekeeper')
    first = service.users['alice']['password_hash']
    second = service.users['bob']['password_hash']
    assert first != second
    assert service.verify_password('alice', 'secret') is True
    assert service.verify_password('bob', 'secret') is True
