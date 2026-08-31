
import os
import threading
import time
import uuid
from typing import Dict

import werkzeug
from flask import Flask, jsonify, redirect, render_template, request, session
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from backend.auth import AUTH_SERVICE, AuthService
from blockchain.ledger import BlockchainLedger
from blockchain.pbft import PBFTValidator
from consumer_web.site import render_verification_page
from database.sqlite_store import MockERPBackend

if not hasattr(werkzeug, '__version__'):
    werkzeug.__version__ = '3.0.0'


app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('HONEYCHAIN_SECRET_KEY', os.getenv('JWT_SECRET', 'dev-secret-key'))

if os.getenv('ENVIRONMENT') == 'production' and not os.getenv('DATABASE_URL'):
    raise RuntimeError('DATABASE_URL is required in production.')

_MAX_BODY_BYTES = int(os.getenv('HONEYCHAIN_MAX_BODY_BYTES', '1048576'))
_LOGIN_RATE_LIMIT = int(os.getenv('HONEYCHAIN_LOGIN_RATE_LIMIT', '5'))
_LOGIN_RATE_WINDOW = int(os.getenv('HONEYCHAIN_LOGIN_RATE_WINDOW', '60'))
_VERIFY_RATE_LIMIT = int(os.getenv('HONEYCHAIN_VERIFY_RATE_LIMIT', '30'))
_VERIFY_RATE_WINDOW = int(os.getenv('HONEYCHAIN_VERIFY_RATE_WINDOW', '60'))
DB_BACKEND = MockERPBackend()
app.config['MAX_CONTENT_LENGTH'] = _MAX_BODY_BYTES


def _build_pbft_cluster():
    nodes = []
    private_keys = {}
    for node_id in ('validator-1', 'validator-2', 'validator-3', 'validator-4'):
        private_key = Ed25519PrivateKey.generate()
        private_keys[node_id] = private_key
        nodes.append({
            'node_id': node_id,
            'public_key': private_key.public_key().public_bytes_raw().hex(),
        })
    return PBFTValidator(nodes), private_keys


PBFT, VALIDATOR_PRIVATE_KEYS = _build_pbft_cluster()
LEDGER = BlockchainLedger(DB_BACKEND.list_blocks())


def _allowed_cors_origins():
    configured = os.getenv('FRONTEND_URL') or os.getenv('CORS_ALLOWED_ORIGINS', '')
    origins = {item.strip() for item in configured.split(',') if item.strip()}
    if os.getenv('ENVIRONMENT', 'development') != 'production':
        origins.update({'http://localhost:3000', 'http://127.0.0.1:3000', 'http://localhost:5173', 'http://127.0.0.1:5173'})
    return sorted(origins)


@app.after_request
def add_cors_headers(response):
    origin = request.headers.get('Origin')
    allowed = _allowed_cors_origins()
    if origin and (origin in allowed or origin.startswith('http://localhost') or origin.startswith('http://127.0.0.1')):
        response.headers['Access-Control-Allow-Origin'] = origin
        response.headers['Access-Control-Allow-Credentials'] = 'true'
        response.headers['Vary'] = 'Origin'
    if request.method == 'OPTIONS':
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
    return response


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
VERIFY_RATE_LIMITER = RateLimiter(_VERIFY_RATE_LIMIT, _VERIFY_RATE_WINDOW)


def _current_user():
    username = session.get('user')
    if username:
        return username
    username = request.headers.get('X-Username') or request.headers.get('X-User')
    if not username:
        return None
    password = request.headers.get('X-Password') or request.headers.get('X-Auth-Password')
    if not password:
        return None
    if AUTH_SERVICE.authenticate(username, password):
        session['user'] = username
        return username
    return None


def _require_auth(required_roles=None):
    username = _current_user()
    if username is None:
        return False, None
    user_record = AUTH_SERVICE.users.get(username)
    if user_record is None:
        return False, None
    if required_roles:
        role = user_record.get('role')
        if role not in required_roles:
            return False, user_record
    return True, user_record


@app.before_request
def enforce_body_limit():
    content_length = request.content_length or 0
    if content_length > _MAX_BODY_BYTES:
        return jsonify({'error': 'request_too_large'}), 413


@app.before_request
def enforce_rate_limits():
    if request.path == '/api/login' and request.method == 'POST':
        client_ip = request.remote_addr or 'unknown'
        if not LOGIN_RATE_LIMITER.is_allowed(client_ip):
            return jsonify({'error': 'rate_limited'}), 429
    if request.path == '/api/verify' and request.method == 'POST':
        client_ip = request.remote_addr or 'unknown'
        if not VERIFY_RATE_LIMITER.is_allowed(client_ip):
            return jsonify({'error': 'rate_limited'}), 429


@app.route('/healthz', methods=['GET'])
def healthz():
    return jsonify({'status': 'ok', 'service': 'honeychain-api'}), 200


@app.route('/health', methods=['GET'])
def health():
    return healthz()


@app.route('/readiness', methods=['GET'])
def readiness():
    if not DB_BACKEND.check_connection():
        return jsonify({'status': 'not_ready', 'database': 'unavailable'}), 503
    return jsonify({'status': 'ready', 'database': 'ok'}), 200


@app.route('/')
def index():
    if session.get('user'):
        return redirect('/dashboard')
    return render_template('login.html')


@app.route('/login', methods=['GET'])
def login_page():
    return render_template('login.html')


@app.route('/dashboard', methods=['GET'])
def dashboard_page():
    username = session.get('user')
    if not username:
        return redirect('/login')
    batches = DB_BACKEND.list_batches() or []
    return render_template('dashboard.html', username=username, batches=batches)


@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')


@app.route('/api/login', methods=['POST'])
def login():
    payload = request.get_json(silent=True) or {}
    username = str(payload.get('username', '')).strip()
    password = str(payload.get('password', ''))
    user = AUTH_SERVICE.authenticate(username, password)
    if user is None:
        return jsonify({'success': False, 'error': 'invalid_credentials'}), 401
    session['user'] = username
    session['role'] = user['role']
    return jsonify({'success': True, 'user': {'username': user['username'], 'role': user['role']}}), 200


@app.route('/api/batches', methods=['GET'])
def list_batches_api():
    ok, _ = _require_auth(required_roles={'beekeeper', 'processor', 'quality_lab', 'distributor', 'retailer', 'consumer'})
    if not ok:
        return jsonify({'error': 'unauthorized'}), 401
    return jsonify({'batches': DB_BACKEND.list_batches() or []}), 200


@app.route('/api/batches', methods=['POST'])
def create_batch():
    ok, user_record = _require_auth(required_roles={'beekeeper', 'processor'})
    if not ok:
        return jsonify({'error': 'unauthorized'}), 401
    payload = request.get_json(silent=True) or {}
    batch = dict(payload)
    batch_id = str(batch.get('batch_id') or uuid.uuid4())
    qr_id = str(batch.get('qr_id') or uuid.uuid4())
    batch['batch_id'] = batch_id
    batch['qr_id'] = qr_id
    batch['owner'] = session.get('user')
    batch['created_by'] = session.get('user')
    if DB_BACKEND.get_batch(batch_id=batch_id) is not None:
        return jsonify({'error': 'duplicate_batch_id'}), 409
    proposal = {'batch_id': batch_id, 'qr_id': batch['qr_id'], 'origin': batch.get('origin', '')}
    proposal_bytes = PBFT._proposal_bytes(proposal)
    signatures = {
        node_id: private_key.sign(proposal_bytes)
        for node_id, private_key in VALIDATOR_PRIVATE_KEYS.items()
    }
    if not PBFT.validate_proposal(proposal, signatures):
        return jsonify({'error': 'consensus_failed'}), 503
    block_record = LEDGER.add_block({
        'transaction': 'CREATE_BATCH',
        'proposal': proposal,
        'consensus': {
            'phase': 'FINALIZE',
            'prepare_count': len(signatures),
            'commit_count': len(signatures),
            'quorum': PBFT.quorum_size,
        },
    })
    try:
        saved_batch_id = DB_BACKEND.add_batch(batch)
        DB_BACKEND.add_block(block_record)
    except ValueError:
        return jsonify({'error': 'duplicate_batch_id'}), 409
    return jsonify({
        'batch_id': saved_batch_id,
        'block_hash': block_record['hash'],
        'consensus': block_record['block']['consensus'],
    }), 201


@app.route('/api/batches/<batch_id>', methods=['GET'])
def get_batch(batch_id):
    ok, user_record = _require_auth(required_roles={'beekeeper', 'processor', 'quality_lab', 'distributor', 'retailer', 'consumer'})
    if not ok:
        return jsonify({'error': 'unauthorized'}), 401
    batch = DB_BACKEND.get_batch(batch_id=batch_id)
    if batch is None:
        return jsonify({'error': 'batch_not_found'}), 404
    current_user = session.get('user') or _current_user()
    if current_user and batch.get('owner') not in (None, current_user):
        return jsonify({'error': 'forbidden'}), 403
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


@app.route('/verify/<qr_id>', methods=['GET'])
def public_verify_page(qr_id):
    batch = DB_BACKEND.get_batch(qr_id=qr_id)
    if batch is None:
        return render_verification_page({'status': 'verification_failed'}), 404
    return render_verification_page(batch), 200


def create_app():
    return app


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', '8000')))
