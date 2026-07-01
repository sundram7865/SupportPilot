def test_root_endpoint(client):
    response = client.get("/")

    assert response.status_code == 200

    data = response.json()

    assert data["service"] == "SupportPilot API"
    assert data["docs"] == "/docs"


def test_openapi_schema_available(client):
    response = client.get("/openapi.json")

    assert response.status_code == 200

    data = response.json()

    assert data["info"]["title"] == "SupportPilot API"
    assert "paths" in data
    assert "/tickets" in data["paths"]


def test_health_endpoint(client):
    response = client.get("/health")

    assert response.status_code == 200

    data = response.json()

    assert isinstance(data, dict)


def test_ready_endpoint(client):
    response = client.get("/ready")

    assert response.status_code in {200, 503}

    data = response.json()

    assert isinstance(data, dict)