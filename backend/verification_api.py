
import logging
from typing import Optional

from database.sqlite_store import MockERPBackend

logger = logging.getLogger(__name__)


class VerificationAPI:
    def __init__(self, backend: Optional[MockERPBackend] = None):
        self.backend = backend or MockERPBackend()

    def verify_batch(self, batch_id: Optional[str] = None, qr_id: Optional[str] = None):
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
