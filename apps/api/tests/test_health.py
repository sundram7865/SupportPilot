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


def test_internal_sla_job_requires_secret(client):
    unauthorized = client.post("/internal/jobs/check-sla")

    assert unauthorized.status_code == 401

    authorized = client.post(
        "/internal/jobs/check-sla",
        headers={"x-internal-job-secret": "dev-internal-job-secret"},
    )

    assert authorized.status_code == 200
    data = authorized.json()
    assert data["ok"] is True
    assert "checked" in data
    assert "changed" in data