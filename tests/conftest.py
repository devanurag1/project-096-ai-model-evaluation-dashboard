"""Pytest configuration and test fixtures."""
import os
import shutil
import tempfile
import pytest
from pathlib import Path
from fastapi.testclient import TestClient

from app.main import app
from app.config import settings
from app.audit.ledger import AuditLedger
import app.audit.ledger as ledger_module
from app.services.eval_service import EvaluationService
import app.services.eval_service as eval_module


@pytest.fixture(autouse=True)
def isolated_test_environment(tmp_path):
    """Isolate DB, audit ledger, and state per test."""
    temp_ledger_path = tmp_path / "test_audit_ledger.jsonl"

    # Instantiate isolated audit ledger
    isolated_ledger = AuditLedger(ledger_path=temp_ledger_path, hmac_key="test-secret-hmac-key")
    ledger_module.audit_ledger = isolated_ledger

    # Instantiate fresh evaluation service
    isolated_eval_service = EvaluationService()
    eval_module.eval_service = isolated_eval_service

    yield

    # Clean up
    if temp_ledger_path.exists():
        temp_ledger_path.unlink()


@pytest.fixture
def client():
    """FastAPI TestClient fixture."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def headers_business():
    return {"X-User-Role": "business_user"}


@pytest.fixture
def headers_engineer():
    return {"X-User-Role": "eval_engineer"}


@pytest.fixture
def headers_compliance():
    return {"X-User-Role": "compliance_officer"}


@pytest.fixture
def headers_admin():
    return {"X-User-Role": "secops_admin"}
