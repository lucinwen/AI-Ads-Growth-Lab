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


def test_csv_validation_endpoint():
    csv_body = (
        "data_mode,impressions,clicks,landing_page_views,add_to_cart,purchases,refunded_orders,spend_usd,attributed_revenue_usd\n"
        "SIMULATED,1000,20,18,5,2,0,20,60\n"
    )
    response = client.post(
        "/v1/import/csv/validate?data_mode=SIMULATED",
        files={"file": ("metrics.csv", csv_body, "text/csv")}
    )
    assert response.status_code == 200
    assert response.json()["validated_rows"] == 1
    assert response.json()["aggregate"]["metrics"]["roas"] == 3


def test_csv_mode_mismatch_rejected():
    csv_body = (
        "data_mode,impressions,clicks,landing_page_views,add_to_cart,purchases,refunded_orders,spend_usd,attributed_revenue_usd\n"
        "REAL,1000,20,18,5,2,0,20,60\n"
    )
    response = client.post(
        "/v1/import/csv/validate?data_mode=SIMULATED",
        files={"file": ("metrics.csv", csv_body, "text/csv")}
    )
    assert response.status_code == 422


def test_demo_overview_endpoint():
    response = client.get("/v1/demo/overview")
    assert response.status_code == 200
    payload = response.json()
    assert payload["data_mode"] == "SIMULATED"
    assert payload["row_count"] == 84
    assert payload["creative_count"] == 12
    assert len(payload["daily"]) == 7
    assert len(payload["funnel"]) == 5
    assert "synthetic" in payload["limitations"][0].lower()


def test_demo_overview_endpoint():
    response = client.get("/v1/demo/overview")
    assert response.status_code == 200
    payload = response.json()
    assert payload["data_mode"] == "SIMULATED"
    assert payload["row_count"] == 84
    assert payload["creative_count"] == 12
    assert len(payload["daily"]) == 7
    assert len(payload["funnel"]) == 5
    assert "synthetic" in payload["limitations"][0].lower()


def test_demo_overview_is_cors_accessible_from_local_frontend():
    response = client.options(
        "/v1/demo/overview",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"
