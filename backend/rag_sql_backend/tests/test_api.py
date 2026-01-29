import sys
import os

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, BASE_DIR)

import pytest
from fastapi.testclient import TestClient

import main
from main import app

client_api = TestClient(app)

@pytest.fixture(autouse=True)
def mock_ollama(monkeypatch):
    def fake_generate_sql(*args, **kwargs):
        return "SELECT * FROM transactions LIMIT 1;"
    monkeypatch.setattr(main, "generate_sql_with_ollama", fake_generate_sql)

def test_root():
    r = client_api.get("/")
    assert r.status_code == 200

def test_sql_endpoint_success():
    r = client_api.post("/api/sql", json={"prompt": "show users"})
    assert r.status_code == 200
    assert r.json()["success"] is True

def test_sql_validation_error():
    r = client_api.post("/api/sql", json={})
    assert r.status_code == 422
