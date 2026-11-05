"""Role-Based Access Control (RBAC) and least privilege tests."""
from fastapi.testclient import TestClient


def test_business_user_cannot_run_evaluations(client: TestClient, headers_business):
    """Least privilege: business_user is restricted from triggering evaluation runs."""
    response = client.post(
        "/api/eval/run",
        json={"model_id": "model-gpt4o"},
        headers=headers_business,
    )
    assert response.status_code == 403
    detail = response.json()["detail"]
    assert detail["error"] == "AccessDenied"
    assert "evaluations:run" in detail["required_permission"]


def test_business_user_cannot_view_audit_records(client: TestClient, headers_business):
    """Least privilege: business_user cannot view raw audit records."""
    response = client.get("/api/audit/records", headers=headers_business)
    assert response.status_code == 403
    assert response.json()["detail"]["error"] == "AccessDenied"


def test_eval_engineer_can_run_eval_but_cannot_grant_exceptions(client: TestClient, headers_engineer):
    """Separation of duties: eval_engineer can run evaluations, but cannot grant exceptions."""
    # 1. Allowed to run eval
    res_run = client.post(
        "/api/eval/run",
        json={"model_id": "model-gpt4o"},
        headers=headers_engineer,
    )
    assert res_run.status_code == 200

    # 2. Forbidden from granting exception
    res_exc = client.post(
        "/api/policies/exceptions",
        json={
            "model_id": "model-ultramega-max",
            "rule_id": "CTL-CST-03",
            "reason": "Engineer trying to bypass cost limit",
            "compensating_control": "None",
            "duration_days": 14,
        },
        headers=headers_engineer,
    )
    assert res_exc.status_code == 403
    assert res_exc.json()["detail"]["error"] == "AccessDenied"


def test_compliance_officer_can_grant_valid_exception(client: TestClient, headers_compliance):
    """Compliance officer is authorized to issue cryptographic exception tokens."""
    res_exc = client.post(
        "/api/policies/exceptions",
        json={
            "model_id": "model-ultramega-max",
            "rule_id": "CTL-CST-03",
            "reason": "Authorized for quarterly portfolio stress-testing",
            "compensating_control": "Hard budget allocation of $5,000 via AWS Cost Explorer budget rule",
            "duration_days": 30,
        },
        headers=headers_compliance,
    )
    assert res_exc.status_code == 200
    data = res_exc.json()
    assert data["token_id"].startswith("EXC-")
    assert len(data["signature"]) == 64
