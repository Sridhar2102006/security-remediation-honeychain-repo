
from consumer_web.site import render_verification_page


def test_html_escaping_renders_script_as_text():
    page = render_verification_page({'batch_id': '<script>alert(1)</script>', 'origin': 'north'})
    assert '<script>' not in page
    assert '&lt;script&gt;alert(1)&lt;/script&gt;' in page
