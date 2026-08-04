import os
from pathlib import Path
from tempfile import gettempdir

from fastapi.testclient import TestClient

test_database = Path(gettempdir()) / "collision-repair-order-summarizer-api-test.db"
test_database.unlink(missing_ok=True)
os.environ["DATABASE_PATH"] = str(test_database)
os.environ["OPENAI_API_KEY"] = ""

from app.main import app  # noqa: E402

client = TestClient(app)

SAMPLE_PAYLOAD = {
    "reference_id": "SYN-1001",
    "customer_name": "Jordan Rivera",
    "vehicle": "2021 Toyota RAV4",
    "workflow_notes": "RO has teardown complete, supplement pending, bumper cover received, liftgate trim backordered, customer last updated three days ago.",
    "source_records": {
        "repair_order": "SYN-RO-1001",
        "claim_status": "To Validate",
        "data_policy": "synthetic demo data only",
    },
    "attachments": ["synthetic_estimate.txt", "synthetic_photos_manifest.json"],
    "requested_by": "Portfolio Demo",
}


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_create_without_api_key_uses_fallback():
    response = client.post("/v1/repair-order-summaries", json=SAMPLE_PAYLOAD)
    assert response.status_code == 201
    body = response.json()
    assert body["model"] == "rule-based-fallback"
    assert "open_blockers" in body["assessment"]


def test_validation_rejects_missing_workflow_notes():
    payload = dict(SAMPLE_PAYLOAD)
    payload.pop("workflow_notes")
    response = client.post("/v1/repair-order-summaries", json=payload)
    assert response.status_code == 422


def test_create_list_and_get_record():
    request_id = "test-request-123"
    created = client.post("/v1/repair-order-summaries", headers={"x-request-id": request_id}, json=SAMPLE_PAYLOAD)
    assert created.status_code == 201
    assert created.json()["request_id"] == request_id

    listed = client.get("/v1/repair-order-summaries?limit=10")
    assert listed.status_code == 200
    assert any(record["request_id"] == request_id for record in listed.json()["records"])

    retrieved = client.get(f"/v1/repair-order-summaries/{request_id}")
    assert retrieved.status_code == 200
    assert retrieved.json()["request"]["workflow_notes"] == SAMPLE_PAYLOAD["workflow_notes"]


def test_list_bounds_limit():
    response = client.get("/v1/repair-order-summaries?limit=1000")
    assert response.status_code == 200
    assert len(response.json()["records"]) <= 100


def test_get_unknown_record_returns_404():
    response = client.get("/v1/repair-order-summaries/not-found")
    assert response.status_code == 404
