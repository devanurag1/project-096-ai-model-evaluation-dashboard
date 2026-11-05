"""Tests for the primary evaluation workflow and comparison matrix."""
from fastapi.testclient import TestClient


def test_health_check_endpoint(client: TestClient):
    """Verify health endpoint returns 200 and checks subsystem statuses."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "HEALTHY"
    assert data["audit_chain_healthy"] is True
    assert "policy_engine" in data["dependencies"]
    assert "audit_ledger" in data["dependencies"]


def test_list_registered_models(client: TestClient, headers_business):
    """Verify registered models can be listed by any authenticated role."""
    response = client.get("/api/models", headers=headers_business)
    assert response.status_code == 200
    models = response.json()
    assert len(models) >= 5
    ids = [m["id"] for m in models]
    assert "model-gpt4o" in ids
    assert "model-llama3-70b" in ids


def test_evaluate_passing_model_happy_path(client: TestClient, headers_engineer):
    """Happy path: Evaluation of high-performing model passes all gates."""
    response = client.post(
        "/api/eval/run",
        json={"model_id": "model-gpt4o"},
        headers=headers_engineer,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "APPROVED_PRODUCTION"
    assert data["policy_summary"]["overall_status"] == "PASS"
    assert data["policy_summary"]["failed_rules"] == 0
    assert len(data["evidence_hash"]) == 64
    assert data["metrics"]["accuracy"] >= 0.82
    assert data["metrics"]["latency_p95_ms"] <= 1200.0


def test_evaluate_failing_model_legacy(client: TestClient, headers_engineer):
    """Verification: Legacy unaligned model fails multiple controls and is rejected."""
    response = client.post(
        "/api/eval/run",
        json={"model_id": "model-legacy-finllm-13b"},
        headers=headers_engineer,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "REJECTED_GOVERNANCE_GATE"
    assert data["policy_summary"]["overall_status"] == "FAIL"
    assert data["policy_summary"]["failed_rules"] > 0


def test_model_comparison_matrix(client: TestClient, headers_business):
    """Verify side-by-side comparison across Accuracy, Latency, Cost, and Safety."""
    response = client.get("/api/eval/compare", headers=headers_business)
    assert response.status_code == 200
    data = response.json()
    assert data["models_evaluated"] >= 5
    assert len(data["comparison_table"]) >= 5
    assert data["recommended_model"] is not None
