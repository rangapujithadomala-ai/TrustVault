def test_home_page(client):
    """Check whether the TrustVault home page is working."""

    response = client.get("/")

    assert response.status_code == 200
    assert b"TrustVault is running!" in response.data