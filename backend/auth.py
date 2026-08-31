
import hashlib
import hmac
import os
from typing import Any, Dict, Optional


class AuthService:
    """Authenticate users using a per-user scrypt hash with a random salt.

    The hash format is: scrypt$<salt_hex>$<n>$<r>$<p>$<digest_hex>
    where n, r, and p are the work parameters. This is a proper KDF and permits
    safe migration from older hashes by comparing against both the current scheme
    and legacy SHA-256 values when present.
    """

    DEFAULT_N = 2 ** 14
    DEFAULT_R = 8
    DEFAULT_P = 1

    def __init__(self, users: Optional[Dict[str, Dict[str, Any]]] = None):
        self.users = dict(users or {})

    def user_exists(self, username: str) -> bool:
        return username in self.users

    def _hash_password(self, password: str, salt: bytes) -> bytes:
        return hashlib.scrypt(
            password.encode('utf-8'),
            salt=salt,
            n=self.DEFAULT_N,
            r=self.DEFAULT_R,
            p=self.DEFAULT_P,
            dklen=32,
        )

    def _legacy_sha256_hash(self, password: str) -> str:
        return hashlib.sha256(password.encode('utf-8')).hexdigest()

    def _serialize_hash(self, password: str, salt: bytes) -> str:
        digest = self._hash_password(password, salt)
        return f'scrypt${salt.hex()}${self.DEFAULT_N}${self.DEFAULT_R}${self.DEFAULT_P}${digest.hex()}'

    def _verify_hash(self, password: str, stored_hash: str) -> bool:
        if not stored_hash or '$' not in stored_hash:
            return False
        scheme, salt_hex, n, r, p, digest_hex = stored_hash.split('$')
        if scheme == 'scrypt':
            try:
                salt = bytes.fromhex(salt_hex)
                n_val = int(n)
                r_val = int(r)
                p_val = int(p)
                expected = hashlib.scrypt(
                    password.encode('utf-8'),
                    salt=salt,
                    n=n_val,
                    r=r_val,
                    p=p_val,
                    dklen=32,
                ).hex()
                return hmac.compare_digest(expected, digest_hex)
            except (ValueError, TypeError):
                return False
        if scheme == 'sha256':
            return hmac.compare_digest(self._legacy_sha256_hash(password), digest_hex)
        return False

    def register_user(self, username: str, password: str, role: str = 'stakeholder') -> Dict[str, Any]:
        if not username:
            raise ValueError('username is required')
        if not password:
            raise ValueError('password is required')
        salt = os.urandom(16)
        record = {
            'username': username,
            'password_hash': self._serialize_hash(password, salt),
            'role': role,
        }
        self.users[username] = record
        return record

    def verify_password(self, username: str, password: str) -> bool:
        user = self.users.get(username)
        if user is None:
            return False
        stored_hash = user.get('password_hash')
        return self._verify_hash(password, stored_hash)

    def authenticate(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        if not self.verify_password(username, password):
            return None
        return dict(self.users.get(username, {}))

    def list_users(self):
        return {name: dict(user) for name, user in self.users.items()}

    def has_role(self, username: str, required_role: str) -> bool:
        user = self.users.get(username)
        if user is None:
            return False
        return user.get('role') == required_role


def build_auth_service() -> AuthService:
    return AuthService()


AUTH_SERVICE = build_auth_service()
