def test_root_reports_service_identity(client):
    response = client.get("/")
    assert response.status_code == 200

    body = response.json()
    assert body["service"] == "DeepShieldAI API"
    assert body["status"] == "ok"


def test_liveness_probe(client):
    """Used by Docker's HEALTHCHECK — see docker-compose.yml / docs/DOCKER.md."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}
