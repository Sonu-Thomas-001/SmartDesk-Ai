"""Integration tests for the Flask endpoints."""

import pytest

from app.main import app


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


def test_health(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "healthy"


def test_recent_empty(client):
    resp = client.get("/api/recent")
    assert resp.status_code == 200
    assert "results" in resp.get_json()


def test_stats(client):
    resp = client.get("/api/stats")
    assert resp.status_code == 200
    data = resp.get_json()
    assert "knowledge_base_size" in data


def test_webhook_requires_sys_id(client):
    resp = client.post("/api/webhook", json={})
    assert resp.status_code == 422


def test_feedback_validation(client):
    resp = client.post("/api/feedback", json={
        "incident_sys_id": "test123",
        "original_assignment": "Network Team",
        "was_correct": True,
    })
    assert resp.status_code == 200
    assert resp.get_json()["status"] == "recorded"
