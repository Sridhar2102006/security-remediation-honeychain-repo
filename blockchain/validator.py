
import base64
import json
import os
from pathlib import Path

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey


class ValidatorNode:
    def __init__(self, node_id, private_key=None, public_key=None, storage_path=None):
        self.node_id = node_id
        self.private_key = private_key
        self.public_key = public_key or (private_key.public_key() if private_key else None)
        self.storage_path = storage_path or os.getenv('HONEYCHAIN_KEYSTORE_PATH', str(Path.cwd() / 'keys'))

    @classmethod
    def create(cls, node_id, storage_path=None):
        private_key = Ed25519PrivateKey.generate()
        instance = cls(node_id=node_id, private_key=private_key, storage_path=storage_path)
        instance.save_to_storage()
        return instance

    @classmethod
    def load_from_storage(cls, node_id, storage_path=None):
        storage_root = storage_path or os.getenv('HONEYCHAIN_KEYSTORE_PATH', str(Path.cwd() / 'keys'))
        path = Path(storage_root) / f'{node_id}.json'
        if not path.exists():
            raise FileNotFoundError(f'No key material found for {node_id}')
        data = json.loads(path.read_text())
        key_hex = data.get('private_key')
        encryption_key = os.getenv('HONEYCHAIN_KEY_ENCRYPTION_KEY')
        if encryption_key:
            raw = base64.urlsafe_b64decode(key_hex.encode())
            key_hex = Fernet(encryption_key.encode()).decrypt(raw).decode()
        private_key = Ed25519PrivateKey.from_private_bytes(bytes.fromhex(key_hex))
        return cls(node_id=node_id, private_key=private_key, storage_path=str(storage_root))

    def save_to_storage(self):
        storage_root = Path(self.storage_path)
        storage_root.mkdir(parents=True, exist_ok=True)
        key_bytes = self.private_key.private_bytes_raw()
        key_text = key_bytes.hex()
        encryption_key = os.getenv('HONEYCHAIN_KEY_ENCRYPTION_KEY')
        if encryption_key:
            token = Fernet(encryption_key.encode()).encrypt(key_text.encode())
            record = {'private_key': base64.urlsafe_b64encode(token).decode()}
        else:
            record = {'private_key': key_text}
        path = storage_root / f'{self.node_id}.json'
        path.write_text(json.dumps(record))
        return path

    def get_public_key_bytes(self):
        return self.public_key.public_bytes_raw()
