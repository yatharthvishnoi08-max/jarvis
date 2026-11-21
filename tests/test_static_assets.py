from fastapi.testclient import TestClient


def test_assets_stay_inside_frontend_directory(tmp_path, monkeypatch):
    import server
    root = tmp_path / 'web_dist'
    root.mkdir()
    (root / 'index.html').write_text('<h1>Jarvis fixture</h1>')
    (root / 'app.js').write_text('fixture asset')
    (tmp_path / 'outside.txt').write_text('must never be served')
    monkeypatch.setattr(server, 'WEB_DIST_DIR', root)
    with TestClient(server.app) as client:
        assert client.get('/app.js').text == 'fixture asset'
        assert 'Jarvis fixture' in client.get('/some-ui-route').text
        for path in ('/%2e%2e/outside.txt', '/..%2foutside.txt'):
            response = client.get(path)
            assert response.status_code == 403
            assert 'must never be served' not in response.text
