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

def test_workspace_product_claim_creative_and_experiment_persistence():
    workspace_response = client.post("/v1/workspaces", json={
        "name": "API Test Workspace", "market": "US",
        "vertical": "beauty_skincare", "data_mode": "SIMULATED"
    })
    assert workspace_response.status_code == 201
    workspace = workspace_response.json()
    workspace_id = workspace["id"]

    product_response = client.post("/v1/products", json={
        "workspace_id": workspace_id, "name": "Test Moisturizer",
        "category": "moisturizer", "currency": "USD",
        "price_cents": 2800, "facts": {"brand": "Test"}
    })
    assert product_response.status_code == 201
    product = product_response.json()

    invalid_claim = client.post("/v1/claims", json={
        "product_id": product["id"], "claim_text": "Clinically proven",
        "claim_type": "clinical", "status": "VERIFIED", "evidence_refs": []
    })
    assert invalid_claim.status_code == 422

    claim_response = client.post("/v1/claims", json={
        "product_id": product["id"], "claim_text": "Daily moisturizer",
        "claim_type": "product_identity", "status": "UNVERIFIED"
    })
    assert claim_response.status_code == 201
    assert claim_response.json()["status"] == "UNVERIFIED"
    claim_id = claim_response.json()["id"]
    no_evidence = client.post("/v1/claims/" + claim_id + "/review", json={
        "reviewer_id":"human-reviewer","decision":"VERIFIED","evidence_refs":[],
        "reason":"Cannot verify without substantiation."
    })
    assert no_evidence.status_code == 422
    reviewed = client.post("/v1/claims/" + claim_id + "/review", json={
        "reviewer_id":"human-reviewer","decision":"VERIFIED",
        "evidence_refs":["evidence://product-spec-v1"],
        "reason":"Checked against the supplied product specification."
    })
    assert reviewed.status_code == 201
    assert client.get("/v1/products/" + product["id"] + "/claims").json()[0]["status"] == "VERIFIED"

    creative_response = client.post("/v1/creatives", json={
        "workspace_id": workspace_id, "product_id": product["id"],
        "concept_name": "Routine demo", "angle": "Everyday routine",
        "hook": "A simple step in my morning routine.",
        "hypothesis": "Routine framing may improve product relevance."
    })
    assert creative_response.status_code == 201
    creative = creative_response.json()

    experiment_response = client.post("/v1/experiments", json={
        "workspace_id": workspace_id, "name": "Test creative experiment",
        "hypothesis": "Routine framing changes qualified attention.",
        "channel": "TikTok", "data_mode": "SIMULATED",
        "budget_cap_cents": 50000
    })
    assert experiment_response.status_code == 201
    experiment = experiment_response.json()

    variant_response = client.post(f"/v1/experiments/{experiment['id']}/variants", json={
        "creative_id": creative["id"], "allocation_pct": 100, "role": "TREATMENT"
    })
    assert variant_response.status_code == 201
    variants = client.get("/v1/experiments/" + experiment["id"] + "/variants")
    assert variants.status_code == 200
    assert len(variants.json()) == 1
    saved_experiments = client.get("/v1/workspaces/" + workspace_id + "/experiments")
    assert saved_experiments.json()[0]["variant_count"] == 1

    listed = client.get(f"/v1/workspaces/{workspace_id}/creatives")
    assert listed.status_code == 200
    assert len(listed.json()) == 1

    audit = client.get(f"/v1/workspaces/{workspace_id}/audit")
    assert audit.status_code == 200
    assert len(audit.json()) >= 4


def test_experiment_data_mode_must_match_workspace():
    workspace_response = client.post("/v1/workspaces", json={
        "name": "Mode Isolation Test", "market": "US",
        "vertical": "beauty_skincare", "data_mode": "SIMULATED"
    })
    workspace_id = workspace_response.json()["id"]
    response = client.post("/v1/experiments", json={
        "workspace_id": workspace_id, "name": "Invalid mixed-mode test",
        "hypothesis": "The test must reject a mode mismatch.",
        "channel": "TikTok", "data_mode": "REAL"
    })
    assert response.status_code == 422


def test_asset_version_requires_separate_human_review():
    workspace = client.post("/v1/workspaces", json={"name":"Asset Review Test","market":"US","data_mode":"SIMULATED"}).json()
    product = client.post("/v1/products", json={"workspace_id":workspace["id"],"name":"Review Product","category":"moisturizer"}).json()
    creative = client.post("/v1/creatives", json={
        "workspace_id":workspace["id"],"product_id":product["id"],
        "concept_name":"Review concept","hook":"A product demo",
        "hypothesis":"Product demo may improve understanding."
    }).json()
    asset = client.post("/v1/assets/versions", json={
        "creative_id":creative["id"],"asset_type":"VIDEO",
        "prompt_text":"Draft prompt","model_name":"demo-provider"
    })
    assert asset.status_code == 201
    assert asset.json()["approval_status"] == "PENDING"
    asset_id = asset.json()["id"]

    review = client.post(f"/v1/assets/versions/{asset_id}/review", json={
        "reviewer_id":"portfolio-owner","decision":"NEEDS_CHANGES",
        "reason":"Check product depiction and claim support.",
        "findings":[{"severity":"MEDIUM","issue":"claim evidence missing"}]
    })
    assert review.status_code == 201
    assert review.json()["decision"] == "NEEDS_CHANGES"
    versions = client.get(f"/v1/creatives/{creative['id']}/assets").json()
    assert versions[0]["approval_status"] == "NEEDS_CHANGES"


def test_demo_workspace_is_seeded_with_persistent_creatives():
    overview = client.get("/v1/demo/overview").json()
    workspace_id = overview["workspace_id"]
    response = client.get("/v1/workspaces/" + workspace_id + "/creatives")
    assert response.status_code == 200
    assert len(response.json()) == 4


def test_strategy_agent_requires_configured_provider(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    response = client.post("/v1/agents/creative-strategy/run", json={
        "workspace_id":"demo-us-beauty-workspace",
        "product_id":"demo-luma-dew-moisturizer",
        "audience_hypothesis":"Adults shopping for everyday moisturizer and skincare routines.",
        "campaign_objective":"CONVERSION",
        "concept_count":2,
        "language":"en-US"
    })
    assert response.status_code == 503
    assert "OPENAI_API_KEY" in response.json()["detail"]
    runs = client.get("/v1/workspaces/demo-us-beauty-workspace/agent-runs").json()
    assert runs[0]["agent_name"] == "creative_strategy"
    assert runs[0]["status"] == "FAILED"


def test_strategy_agent_persists_generated_draft_concepts(monkeypatch):
    import app.main as main_module
    from app.agents import CreativeConcept, StrategyOutput

    async def fake_strategy(**kwargs):
        return StrategyOutput(concepts=[
            CreativeConcept(
                concept_name="Routine framing", angle="Everyday ritual",
                hook="A simple step in my morning routine.",
                narrative="Show the product as one item in a daily routine.",
                cta="Explore the product", hypothesis="Routine framing may improve relevance.",
                format="Vertical video · 20s", claims_used=[]
            ),
            CreativeConcept(
                concept_name="Texture detail", angle="Sensory demonstration",
                hook="A closer look at the texture.",
                narrative="Use close-up product shots without unsupported efficacy claims.",
                cta="See product details", hypothesis="Texture detail may increase qualified curiosity.",
                format="Product demo · 15s", claims_used=[]
            )
        ]), "test-model"

    monkeypatch.setattr(main_module, "generate_creative_strategy", fake_strategy)
    response = client.post("/v1/agents/creative-strategy/run", json={
        "workspace_id":"demo-us-beauty-workspace",
        "product_id":"demo-luma-dew-moisturizer",
        "audience_hypothesis":"Adults shopping for everyday moisturizer and skincare routines.",
        "campaign_objective":"CONVERSION",
        "concept_count":2,
        "language":"en-US"
    })
    assert response.status_code == 201
    payload = response.json()
    assert payload["status"] == "SUCCEEDED"
    assert payload["model"] == "test-model"
    assert len(payload["concepts"]) == 2
    assert payload["concepts"][0]["status"] == "DRAFT_REQUIRES_REVIEW"
    saved = client.get("/v1/workspaces/demo-us-beauty-workspace/creatives").json()
    assert any(item["concept_name"] == "Routine framing" for item in saved)
