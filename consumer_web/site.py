
import html


def render_verification_page(batch_record):
    if not batch_record:
        return '<main><h1>HoneyChain</h1><h2>Verification failed</h2><p>We could not verify this QR credential.</p></main>'
    values = []
    for field, value in (batch_record or {}).items():
        safe_value = html.escape(str(value), quote=True)
        values.append(f'<li><strong>{html.escape(str(field), quote=True)}</strong>: {safe_value}</li>')
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        '<title>HoneyChain Product Verification</title>'
        '<style>body{font-family:Arial,sans-serif;background:#f4f8ef;margin:0;color:#173b2d}'
        'main{max-width:680px;margin:40px auto;background:white;padding:28px;border-radius:16px;'
        'box-shadow:0 10px 28px #0001}h1{color:#166044}h2{color:#2b6b43}'
        '.badge{display:inline-block;background:#e2f4df;color:#17603a;padding:8px 12px;'
        'border-radius:999px;font-weight:bold}li{padding:10px;border-bottom:1px solid #e8eee2}'
        '</style></head><body><main><h1>HoneyChain</h1>'
        '<p class="badge">✓ PROVENANCE VERIFIED</p><h2>Authentic product record</h2>'
        '<ul>' + ''.join(values) + '</ul>'
        '<p>Blockchain-backed, tamper-evident traceability record.</p>'
        '</main></body></html>'
    )
