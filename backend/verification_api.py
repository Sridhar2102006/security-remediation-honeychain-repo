
import logging
import threading
import time
from typing import Optional

from database.sqlite_store import MockERPBackend

logger = logging.getLogger(__name__)


class VerificationAPI:
    def __init__(self, backend: Optional[MockERPBackend] = None):
        self.backend = backend or MockERPBackend()
        self._lock = threading.Lock()
        self._attempts = {}

    def _rate_limited(self, client_ip: str = 'unknown', limit: int = 20, window_seconds: int = 60) -> bool:
        now = time.monotonic()
        with self._lock:
            attempts = self._attempts.setdefault(client_ip, [])
            attempts[:] = [ts for ts in attempts if now - ts < window_seconds]
            if len(attempts) >= limit:
                return False
            attempts.append(now)
            return True

    def verify_batch(self, batch_id: Optional[str] = None, qr_id: Optional[str] = None, client_ip: str = 'unknown'):
        if not self._rate_limited(client_ip):
            logger.warning('verification rate limited for client_ip=%s', client_ip)
            return {'success': False, 'reason': 'verification_failed'}
        if batch_id is not None:
            batch = self.backend.get_batch(batch_id=batch_id)
            if batch is None:
                logger.warning('verification failed for batch_id=%s', batch_id)
                return {'success': False, 'reason': 'verification_failed'}
            return {'success': True, 'batch': batch}
        if qr_id is not None:
            batch = self.backend.get_batch(qr_id=qr_id)
            if batch is None:
                logger.warning('verification failed for qr_id=%s', qr_id)
                return {'success': False, 'reason': 'verification_failed'}
            return {'success': True, 'batch': batch}
        logger.warning('verification failed for missing identifiers')
        return {'success': False, 'reason': 'verification_failed'}
