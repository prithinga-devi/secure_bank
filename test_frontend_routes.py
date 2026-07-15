import importlib


def test_home_page_uses_render_backend_links():
    app_module = importlib.import_module('app')
    client = app_module.app.test_client()

    response = client.get('/')

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert 'https://secure-bank-dev8.onrender.com/login/google' in html
    assert 'https://secure-bank-dev8.onrender.com/login' in html
    assert 'GitHub Pages only hosts static content' not in html
