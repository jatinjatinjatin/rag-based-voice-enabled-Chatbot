import sys
import os

# Add backend directory to Python path
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, BASE_DIR)

import pytest
from fastapi.testclient import TestClient

import main
from main import app

client_api = TestClient(app)

# -----------------------------
# Ollama mock
# -----------------------------

@pytest.fixture(autouse=True)
def mock_ollama(monkeypatch):
    def fake_generate_sql(prompt: str) -> str:
        return "SELECT * FROM users;"

    monkeypatch.setattr(main, "generate_sql_with_ollama", fake_generate_sql)

# -----------------------------
# Tests
# -----------------------------

def test_root():
    response = client_api.get("/")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_sql_endpoint_success():
    payload = {"prompt": "show all users"}
    response = client_api.post("/api/sql", json=payload)

    assert response.status_code == 200
    data = response.json()

    assert "sql" in data
    assert data["sql"].lower().startswith("select")
    assert data["success"] is True


def test_sql_validation_error():
    response = client_api.post("/api/sql", json={})
    assert response.status_code == 422
