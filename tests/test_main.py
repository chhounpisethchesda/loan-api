import pytest
from fastapi.testclient import TestClient
from main import app, load_prediction_model

@pytest.fixture(scope="module")
def client():
    load_prediction_model()
    with TestClient(app) as c:
        yield c

def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "model_loaded" in data
    assert data["version"] == "1.0.0"

def test_root_endpoint(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "Loan Prediction Service is operational" in response.json()["message"]

def test_prediction_success(client):
    payload = {
        "borrower_id": 1042,
        "amount_usd": 1500,
        "term_months": 12,
        "province": "Battambang"
    }
    response = client.post("/predictions", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "default_probability" in data
    assert "recommendation" in data
    assert data["recommendation"] in ["approve", "review", "reject"]
    assert "confidence" in data
    assert data["model_version"] == "risk-pipeline-v1.0.0"

def test_prediction_invalid_amount_low(client):
    payload = {
        "borrower_id": 1042,
        "amount_usd": 50,  # Below minimum 100
        "term_months": 12,
        "province": "Battambang"
    }
    response = client.post("/predictions", json=payload)
    assert response.status_code == 422

def test_prediction_invalid_amount_high(client):
    payload = {
        "borrower_id": 1042,
        "amount_usd": 9000,  # Above maximum 5000
        "term_months": 12,
        "province": "Battambang"
    }
    response = client.post("/predictions", json=payload)
    assert response.status_code == 422

def test_list_applications(client):
    response = client.get("/applications")
    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    assert data["total"] >= 3

def test_create_application(client):
    new_app = {
        "borrower_id": 1042,
        "amount_usd": 1500,
        "term_months": 12,
        "purpose": "Buy a rice thresher",
        "phone": "012345678"
    }
    response = client.post("/applications", json=new_app)
    assert response.status_code == 201
    created = response.json()
    assert created["borrower_id"] == 1042
    assert created["amount_usd"] == 1500
    assert created["status"] == "pending"

def test_get_application_by_id(client):
    response = client.get("/applications/101")
    assert response.status_code == 200
    assert response.json()["id"] == 101

def test_get_application_not_found(client):
    response = client.get("/applications/99999")
    assert response.status_code == 404

def test_get_borrower_applications(client):
    response = client.get("/borrowers/1/applications")
    assert response.status_code == 200
    assert len(response.json()["data"]) >= 1
