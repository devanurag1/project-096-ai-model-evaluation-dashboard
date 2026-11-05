"""Production deployment smoke test suite for AI Model Evaluation Dashboard.
Can be executed against a running server (via BASE_URL) or directly via TestClient.
"""
import sys
import os
import json
from pathlib import Path

# Add project root to sys.path
root_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_dir))

from fastapi.testclient import TestClient
from rich.console import Console
from rich.table import Table

from app.main import app


console = Console()


def run_smoke_tests():
    console.print("\n[bold cyan]===========================================================[/bold cyan]")
    console.print("[bold cyan]  AI MODEL EVALUATION DASHBOARD - SMOKE TEST SUITE       [/bold cyan]")
    console.print("[bold cyan]===========================================================[/bold cyan]\n")

    client = TestClient(app)
    results = []

    # 1. Health Endpoint Smoke Test
    try:
        res = client.get("/health")
        if res.status_code == 200 and res.json().get("status") == "HEALTHY":
            results.append(("Health Check Subsystems", "PASS", "Dependencies verified, DB & Ledger intact"))
        else:
            results.append(("Health Check Subsystems", "FAIL", f"Unexpected status: {res.status_code}"))
    except Exception as e:
        results.append(("Health Check Subsystems", "FAIL", str(e)))

    # 2. Primary Workflow: Evaluate Passing Model (GPT-4o)
    try:
        res = client.post(
            "/api/eval/run",
            json={"model_id": "model-gpt4o"},
            headers={"X-User-Role": "eval_engineer"},
        )
        data = res.json()
        if res.status_code == 200 and data.get("status") == "APPROVED_PRODUCTION":
            evidence = data.get("evidence_hash", "")[:12]
            results.append(("Primary Workflow (GPT-4o)", "PASS", f"Approved for production. Evidence: {evidence}..."))
        else:
            results.append(("Primary Workflow (GPT-4o)", "FAIL", f"Status: {data.get('status')}"))
    except Exception as e:
        results.append(("Primary Workflow (GPT-4o)", "FAIL", str(e)))

    # 3. Governance Gate Enforcement: Legacy Model Rejection
    try:
        res = client.post(
            "/api/eval/run",
            json={"model_id": "model-legacy-finllm-13b"},
            headers={"X-User-Role": "eval_engineer"},
        )
        data = res.json()
        if res.status_code == 200 and data.get("status") == "REJECTED_GOVERNANCE_GATE":
            failed = data["policy_summary"]["failed_rules"]
            results.append(("Governance Rejection Gate", "PASS", f"Legacy model blocked correctly ({failed} rules failed)"))
        else:
            results.append(("Governance Rejection Gate", "FAIL", f"Expected rejection, got: {data.get('status')}"))
    except Exception as e:
        results.append(("Governance Rejection Gate", "FAIL", str(e)))

    # 4. Least Privilege Access Control: Business User Blocked
    try:
        res = client.post(
            "/api/eval/run",
            json={"model_id": "model-gpt4o"},
            headers={"X-User-Role": "business_user"},
        )
        if res.status_code == 403:
            results.append(("Least Privilege RBAC", "PASS", "Business viewer blocked with 403 Forbidden"))
        else:
            results.append(("Least Privilege RBAC", "FAIL", f"Expected 403, got {res.status_code}"))
    except Exception as e:
        results.append(("Least Privilege RBAC", "FAIL", str(e)))

    # 5. Cryptographic Audit Chain Verification
    try:
        res = client.get("/api/audit/verify", headers={"X-User-Role": "compliance_officer"})
        data = res.json()
        if res.status_code == 200 and data.get("is_valid") is True:
            records = data.get("total_records", 0)
            results.append(("Cryptographic Audit Chain", "PASS", f"SHA-256 chain & HMAC signatures verified ({records} blocks)"))
        else:
            results.append(("Cryptographic Audit Chain", "FAIL", data.get("verification_message")))
    except Exception as e:
        results.append(("Cryptographic Audit Chain", "FAIL", str(e)))

    # 6. Zero-Tolerance Exception Prohibition (Negative Test)
    try:
        res = client.post(
            "/api/policies/exceptions",
            json={
                "model_id": "model-legacy-finllm-13b",
                "rule_id": "CTL-SAF-04",
                "reason": "Attempting waiver for legacy model",
                "compensating_control": "Firewall egress packet inspection enabled",
                "duration_days": 7,
            },
            headers={"X-User-Role": "compliance_officer"},
        )
        if res.status_code == 400:
            results.append(("Zero-Tolerance Exception Block", "PASS", "PII waiver blocked with 400 Bad Request"))
        else:
            results.append(("Zero-Tolerance Exception Block", "FAIL", f"Expected 400, got {res.status_code}"))
    except Exception as e:
        results.append(("Zero-Tolerance Exception Block", "FAIL", str(e)))

    # 7. Model Comparison Matrix Output
    try:
        res = client.get("/api/eval/compare", headers={"X-User-Role": "business_user"})
        data = res.json()
        if res.status_code == 200 and data.get("models_evaluated") >= 4:
            rec = data.get("recommended_model")
            results.append(("Comparison Matrix", "PASS", f"Comparison table generated. Recommended: {rec}"))
        else:
            results.append(("Comparison Matrix", "FAIL", "Comparison table incomplete"))
    except Exception as e:
        results.append(("Comparison Matrix", "FAIL", str(e)))

    # Print Results Table
    table = Table(title="Smoke Test Execution Summary", show_header=True, header_style="bold magenta")
    table.add_column("Check / Workflow", style="cyan", width=32)
    table.add_column("Result", style="bold", width=10)
    table.add_column("Details", style="dim", width=48)

    all_passed = True
    for name, status_str, detail in results:
        status_styled = "[green]PASS[/green]" if status_str == "PASS" else "[red]FAIL[/red]"
        if status_str != "PASS":
            all_passed = False
        table.add_row(name, status_styled, detail)

    console.print(table)

    if all_passed:
        console.print("\n[bold green]✓ ALL 7 SMOKE TESTS PASSED - PRODUCTION CANDIDATE VERIFIED[/bold green]\n")
        return 0
    else:
        console.print("\n[bold red]✗ SMOKE TEST FAILURES DETECTED - DEPLOYMENT NOT SAFE[/bold red]\n")
        return 1


if __name__ == "__main__":
    sys.exit(run_smoke_tests())
