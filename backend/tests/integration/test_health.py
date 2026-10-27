from fastapi.testclient import TestClient

from app.main import create_app
from app.settings import Settings


def test_health_returns_ok() -> None:
    client = TestClient(create_app(Settings(_env_file=None)))

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
