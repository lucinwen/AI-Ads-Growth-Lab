from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_aggregate_endpoint():
    response = client.post("/v1/metrics/aggregate", json={"rows": [{
        "data_mode": "SIMULATED", "impressions": 1000, "clicks": 20,
        "landing_page_views": 18, "add_to_cart": 5, "purchases": 2,
        "refunded_orders": 0, "spend_usd": 20, "attributed_revenue_usd": 60
    }]})
    assert response.status_code == 200
    assert response.json()["metrics"]["roas"] == 3


def test_mode_mismatch_rejected():
    payload = {"rows": [
        {"data_mode":"SIMULATED","impressions":1,"clicks":1,"landing_page_views":1,"add_to_cart":0,"purchases":0,"refunded_orders":0,"spend_usd":1,"attributed_revenue_usd":0},
        {"data_mode":"REAL","impressions":1,"clicks":1,"landing_page_views":1,"add_to_cart":0,"purchases":0,"refunded_orders":0,"spend_usd":1,"attributed_revenue_usd":0}
    ]}
    response = client.post("/v1/metrics/aggregate", json=payload)
    assert response.status_code == 422
