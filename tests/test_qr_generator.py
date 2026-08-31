
import pytest
from qr_service.generator import QRCodeGenerator


def test_qr_generator_requires_configured_verification_url():
    with pytest.raises(ValueError):
        QRCodeGenerator()

    generator = QRCodeGenerator(verification_url='https://example.test/verify')
    assert generator.generate('B-1').startswith('https://example.test/verify')
