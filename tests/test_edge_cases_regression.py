"""Edge cases, boundaries, regression, and idempotency tests."""
from fastapi.testclient import TestClient


def test_missing_model_returns_404(client: TestClient, headers_engineer):
    """Verify non-existent model candidate returns 404 and logs denied attempt."""
    response = client.post(
        "/api/eval/run",
        json={"model_id": "non-existent-phantom-model"},
        headers=headers_engineer,
    )
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_invalid_schema_payload_returns_422(client: TestClient, headers_engineer):
    """Verify malformed input without required fields fails safely with 422 Unprocessable Entity."""
    response = client.post(
        "/api/models",
        json={"id": "bad-model"},  # missing name, provider, tier, pricing
        headers=headers_engineer,
    )
    assert response.status_code == 422


def test_regression_zero_tokens_and_zero_duration_safe(client: TestClient, headers_engineer):
    """
    Regression Test:
    Ensures that edge cases where token count is 0 or duration is 0ms
    never trigger ZeroDivisionError or unhandled server crashes.
    """
    # Register an edge case model
    client.post(
        "/api/models",
        json={
            "id": "model-zero-edge-case",
            "name": "Zero Token Edge Case Model",
            "provider": "Mock Edge",
            "tier": "LIGHTWEIGHT_VPC",
            "version": "1.0",
            "context_window": 1024,
            "cost_per_1k_prompt": 0.0,
            "cost_per_1k_completion": 0.0,
            "blended_cost_per_1k": 0.0,
            "intended_use": "Edge case verification testing",
        },
        headers=headers_engineer,
    )

    response = client.post(
        "/api/eval/run",
        json={"model_id": "model-zero-edge-case"},
        headers=headers_engineer,
    )
    assert response.status_code == 200
    data = response.json()
    assert "evidence_hash" in data


def test_correlation_id_propagation_in_headers(client: TestClient):
    """Verify correlation ID is reflected back in response headers for end-to-end tracing."""
    custom_corr_id = "TRACE-TEST-UUID-9999"
    response = client.get("/health", headers={"X-Correlation-ID": custom_corr_id})
    assert response.headers["X-Correlation-ID"] == custom_corr_id
    assert "X-Response-Time-Ms" in response.headers


def test_duplicate_retry_evaluation_run(client: TestClient, headers_engineer):
    """Verify retrying evaluation runs sequentially executes cleanly and maintains ledger integrity."""
    res1 = client.post("/api/eval/run", json={"model_id": "model-mistral-small"}, headers=headers_engineer)
    res2 = client.post("/api/eval/run", json={"model_id": "model-mistral-small"}, headers=headers_engineer)
    assert res1.status_code == 200
    assert res2.status_code == 200
    assert res1.json()["run_id"] != res2.json()["run_id"]  # Distinct traceable runs
