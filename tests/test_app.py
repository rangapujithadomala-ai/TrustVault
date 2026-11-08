def test_home_serves_public_landing_page(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"TrustVault" in response.data
    assert b"Privacy Policy" in response.data


def test_privacy_and_terms_pages_load(client):
    assert client.get("/privacy").status_code == 200
    assert client.get("/terms").status_code == 200


def test_security_headers_present(client):
    response = client.get("/")
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert "Content-Security-Policy" in response.headers


def test_login_page_loads(client):
    response = client.get("/login.html")
    assert response.status_code == 200
    assert b"TrustVault" in response.data
