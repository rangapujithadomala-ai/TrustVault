def test_home_redirects_to_login(client):
    response = client.get("/")
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login.html")


def test_login_page_loads(client):
    response = client.get("/login.html")
    assert response.status_code == 200
    assert b"TrustVault" in response.data
