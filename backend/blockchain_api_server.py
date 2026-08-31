
import os
import threading
import time
from typing import Dict

import werkzeug
from flask import Flask, jsonify, request

from backend.auth import AUTH_SERVICE, AuthService
from database.sqlite_store import MockERPBackend

if not hasattr(werkzeug, '__version__'):
    werkzeug.__version__ = '3.0.0'


app = Flask(__name__)

_MAX_BODY_BYTES = int(os.getenv('HONEYCHAIN_MAX_BODY_BYTES', '1048576'))
_LOGIN_RATE_LIMIT = int(os.getenv('HONEYCHAIN_LOGIN_RATE_LIMIT', '5'))
_LOGIN_RATE_WINDOW = int(os.getenv('HONEYCHAIN_LOGIN_RATE_WINDOW', '60'))
DB_BACKEND = MockERPBackend()
app.config['MAX_CONTENT_LENGTH'] = _MAX_BODY_BYTES


def seed_default_users(service: AuthService):
    for username, role in {
        'beekeeper': 'beekeeper',
        'processor': 'processor',
        'quality_lab': 'quality_lab',
        'distributor': 'distributor',
        'retailer': 'retailer',
        'consumer': 'consumer',
    }.items():
        if service.user_exists(username):
            continue
        env_key = f'HONEYCHAIN_{username.upper()}_PASSWORD'
        password = os.getenv(env_key)
        if password:
            service.register_user(username, password, role)


seed_default_users(AUTH_SERVICE)


class RateLimiter:
    def __init__(self, limit: int, window_seconds: int):
        self.limit = limit
        self.window_seconds = window_seconds
        self._attempts: Dict[str, list] = {}
        self._lock = threading.Lock()

    def is_allowed(self, key: str) -> bool:
        now = time.monotonic()
        with self._lock:
            attempts = self._attempts.setdefault(key, [])
            attempts[:] = [ts for ts in attempts if now - ts < self.window_seconds]
            if len(attempts) >= self.limit:
                return False
            attempts.append(now)
            return True


LOGIN_RATE_LIMITER = RateLimiter(_LOGIN_RATE_LIMIT, _LOGIN_RATE_WINDOW)


@app.before_request
def enforce_body_limit():
    content_length = request.content_length or 0
    if content_length > _MAX_BODY_BYTES:
        return jsonify({'error': 'request_too_large'}), 413


@app.before_request
def enforce_login_rate_limit():
    if request.path == '/api/login' and request.method == 'POST':
        client_ip = request.remote_addr or 'unknown'
        if not LOGIN_RATE_LIMITER.is_allowed(client_ip):
            return jsonify({'error': 'rate_limited'}), 429


@app.route('/healthz', methods=['GET'])
def healthz():
    return jsonify({'status': 'ok'}), 200


@app.route('/api/login', methods=['POST'])
def login():
    payload = request.get_json(silent=True) or {}
    username = str(payload.get('username', '')).strip()
    password = str(payload.get('password', ''))
    user = AUTH_SERVICE.authenticate(username, password)
    if user is None:
        return jsonify({'success': False, 'error': 'invalid_credentials'}), 401
    return jsonify({'success': True, 'user': {'username': user['username'], 'role': user['role']}}), 200


@app.route('/api/batches', methods=['POST'])
def create_batch():
    payload = request.get_json(silent=True) or {}
    batch = payload.copy()
    batch_id = DB_BACKEND.add_batch(batch)
    return jsonify({'batch_id': batch_id}), 201


@app.route('/api/batches/<batch_id>', methods=['GET'])
def get_batch(batch_id):
    batch = DB_BACKEND.get_batch(batch_id=batch_id)
    if batch is None:
        return jsonify({'error': 'batch_not_found'}), 404
    return jsonify(batch), 200


@app.route('/api/verify', methods=['POST'])
def verify_batch():
    payload = request.get_json(silent=True) or {}
    batch_id = payload.get('batch_id')
    qr_id = payload.get('qr_id')
    if qr_id and not batch_id:
        batch = DB_BACKEND.get_batch(qr_id=qr_id)
        if batch is None:
            return jsonify({'error': 'verification_failed'}), 404
        return jsonify({'status': 'ok', 'batch_id': batch.get('batch_id'), 'qr_id': qr_id}), 200
    if batch_id:
        batch = DB_BACKEND.get_batch(batch_id=batch_id)
        if batch is None:
            return jsonify({'error': 'verification_failed'}), 404
        return jsonify({'status': 'ok', 'batch_id': batch['batch_id']}), 200
    return jsonify({'error': 'verification_failed'}), 400


def create_app():
    return app


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', '8000')))
