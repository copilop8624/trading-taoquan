import pytest

from web_app import app as flask_app


@pytest.fixture
def client():
    flask_app.config['TESTING'] = True
    with flask_app.test_client() as c:
        yield c


def test_results_empty_shows_hint(client):
    resp = client.get('/results')
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert 'Upload a tradelist from the Dashboard' in html
