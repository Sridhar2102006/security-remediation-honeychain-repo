
import html


def render_verification_page(batch_record):
    values = []
    for field, value in (batch_record or {}).items():
        safe_value = html.escape(str(value), quote=True)
        values.append(f'<li><strong>{html.escape(str(field), quote=True)}</strong>: {safe_value}</li>')
    return '<ul>' + ''.join(values) + '</ul>'
