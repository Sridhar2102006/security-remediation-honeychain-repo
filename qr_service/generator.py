
import hashlib
import hmac
import json
import os
import time
import urllib.parse


class QRCodeGenerator:
    def __init__(self, verification_url=None, config=None):
        config = config or os.environ
        configured_value = verification_url or config.get('VERIFICATION_URL') or config.get('HONEYCHAIN_VERIFICATION_URL')
        if not configured_value:
            raise ValueError('verification_url is required and must be configured via VERIFICATION_URL')
        self.verification_url = configured_value
        if not self.verification_url.startswith('https://'):
            raise ValueError('verification_url must use https')

    def generate(self, batch_id):
        secret = os.getenv('HONEYCHAIN_QR_SIGNING_KEY', 'dev-qr-signing-key')
        payload = json.dumps({'batch_id': str(batch_id), 'ts': int(time.time())}, sort_keys=True)
        signature = hmac.new(secret.encode('utf-8'), payload.encode('utf-8'), hashlib.sha256).hexdigest()
        params = urllib.parse.urlencode({'batch_id': str(batch_id), 'ts': int(time.time()), 'sig': signature})
        return f'{self.verification_url}?{params}'
