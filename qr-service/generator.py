
import os


class QRCodeGenerator:
    def __init__(self, verification_url=None, config=None):
        config = config or os.environ
        configured_value = verification_url or config.get('VERIFICATION_URL') or config.get('HONEYCHAIN_VERIFICATION_URL')
        if not configured_value:
            raise ValueError('verification_url is required and must be configured via VERIFICATION_URL')
        self.verification_url = configured_value

    def generate(self, batch_id):
        return f'{self.verification_url}?batch_id={batch_id}'
