"""Evaluation service coordinating benchmark tests, policy enforcement, and audit evidence."""
import json
import uuid
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional
from app.config import settings
from app.models.domain import (
    ModelCandidate,
    EvaluationRun,
    EvaluationMetrics,
    PolicyStatus,
    ExceptionToken,
    UserRole,
)
from app.audit.hasher import compute_sha256, compute_file_sha256
from app.audit.ledger import audit_ledger
from app.policies.engine import policy_engine
from app.services.model_adapter import model_adapter
from app.security.tokens import verify_exception_token


class EvaluationService:
    """Coordinates end-to-end evaluation runs, policy gate checks, and audit logging."""

    def __init__(self):
        self._lock = threading.Lock()
        self._models: Dict[str, ModelCandidate] = {}
        self._runs: Dict[str, EvaluationRun] = {}
        self._exceptions: Dict[str, ExceptionToken] = {}
        self._load_seed_models()

    def _load_seed_models(self) -> None:
        """Load initial candidate models from sample_data."""
        sample_path = settings.BASE_DIR / "sample_data" / "sample_models.json"
        if sample_path.exists():
            try:
                with open(sample_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for item in data:
                        model = ModelCandidate(**item)
                        self._models[model.id] = model
            except Exception as e:
                print(f"Warning: Failed to load seed models: {e}")

    def list_models(self) -> List[ModelCandidate]:
        """List all registered candidate models."""
        with self._lock:
            return list(self._models.values())

    def get_model(self, model_id: str) -> Optional[ModelCandidate]:
        """Retrieve model by ID."""
        with self._lock:
            return self._models.get(model_id)

    def register_model(self, model: ModelCandidate, actor: str, role: str, correlation_id: str) -> ModelCandidate:
        """Register a new candidate model with audit trail."""
        with self._lock:
            self._models[model.id] = model

        # Record audit log
        audit_ledger.append(
            actor=actor,
            role=role,
            action="MODEL_REGISTER",
            resource=f"model/{model.id}",
            result="ALLOWED",
            reason=f"Registered candidate model '{model.name}' by {actor}",
            correlation_id=correlation_id,
            payload=model.model_dump(),
        )
        return model

    def store_exception_token(self, token: ExceptionToken, actor: str, role: str, correlation_id: str) -> None:
        """Store an authorized cryptographic exception token."""
        with self._lock:
            self._exceptions[token.token_id] = token

        audit_ledger.append(
            actor=actor,
            role=role,
            action="EXCEPTION_GRANT",
            resource=f"model/{token.model_id}:{token.rule_id}",
            result="EXCEPTION_GRANTED",
            reason=f"Compliance exception granted by {actor}: {token.reason}",
            correlation_id=correlation_id,
            payload=token.model_dump(),
        )

    def get_exception_token(self, token_id: str) -> Optional[ExceptionToken]:
        with self._lock:
            return self._exceptions.get(token_id)

    def run_evaluation(
        self,
        model_id: str,
        evaluator_id: str,
        evaluator_role: str,
        correlation_id: str,
        active_exception_tokens: Optional[List[str]] = None,
    ) -> EvaluationRun:
        """Execute evaluation run for candidate model, enforce controls, and record audit evidence."""
        model = self.get_model(model_id)
        if not model:
            # Audit negative attempt
            audit_ledger.append(
                actor=evaluator_id,
                role=evaluator_role,
                action="EVALUATION_RUN",
                resource=f"model/{model_id}",
                result="DENIED",
                reason=f"Model '{model_id}' does not exist in registry.",
                correlation_id=correlation_id,
            )
            raise ValueError(f"Model candidate '{model_id}' not found.")

        # Compute dataset fingerprint for evidence integrity
        dataset_path = settings.FIXTURES_DIR / "benchmark_dataset.json"
        dataset_hash = compute_file_sha256(dataset_path) or compute_sha256("empty-dataset-fallback")

        # Resolve any active exception tokens
        resolved_exceptions: List[ExceptionToken] = []
        if active_exception_tokens:
            for tok_id in active_exception_tokens:
                tok = self.get_exception_token(tok_id)
                if tok and tok.model_id == model_id:
                    resolved_exceptions.append(tok)

        # Generate metrics through adapter
        metrics = model_adapter.generate_metrics_for_model(model)

        # Enforce policy gate rules
        policy_summary = policy_engine.evaluate_model(metrics, resolved_exceptions)

        # Compute cryptographic evidence hash
        evidence_packet = {
            "model_id": model_id,
            "dataset_hash": dataset_hash,
            "metrics": metrics.model_dump(),
            "policy_summary": policy_summary.model_dump(),
            "applied_exceptions": [e.token_id for e in resolved_exceptions],
        }
        evidence_hash = compute_sha256(evidence_packet)

        run_id = f"RUN-{uuid.uuid4().hex[:12].upper()}"

        # Determine run status
        if policy_summary.overall_status == PolicyStatus.PASS:
            run_status = "APPROVED_PRODUCTION"
            audit_result = "ALLOWED"
        elif policy_summary.overall_status == PolicyStatus.EXCEPTION_APPROVED:
            run_status = "APPROVED_WITH_EXCEPTION"
            audit_result = "EXCEPTION_GRANTED"
        else:
            run_status = "REJECTED_GOVERNANCE_GATE"
            audit_result = "DENIED"

        run = EvaluationRun(
            run_id=run_id,
            model_id=model_id,
            model_name=model.name,
            evaluator=evaluator_id,
            evaluator_role=evaluator_role,
            evaluated_at=datetime.now(timezone.utc).isoformat(),
            dataset_version="financial-qa-v1.4",
            dataset_hash=dataset_hash,
            metrics=metrics,
            policy_summary=policy_summary,
            applied_exceptions=resolved_exceptions,
            evidence_hash=evidence_hash,
            status=run_status,
            correlation_id=correlation_id,
        )

        with self._lock:
            self._runs[run_id] = run
            # Update model status in registry
            model.status = run_status

        # Append immutable audit evidence record
        audit_ledger.append(
            actor=evaluator_id,
            role=evaluator_role,
            action="EVALUATION_RUN",
            resource=f"eval_run/{run_id}",
            result=audit_result,
            reason=policy_summary.summary_message,
            correlation_id=correlation_id,
            payload={
                "run_id": run_id,
                "model_id": model_id,
                "overall_status": policy_summary.overall_status.value,
                "evidence_hash": evidence_hash,
                "failed_rules": policy_summary.failed_rules,
                "passed_rules": policy_summary.passed_rules,
            },
        )

        return run

    def list_runs(self) -> List[EvaluationRun]:
        """List all evaluation runs in reverse chronological order."""
        with self._lock:
            return list(reversed(list(self._runs.values())))

    def get_run(self, run_id: str) -> Optional[EvaluationRun]:
        """Get evaluation run by ID."""
        with self._lock:
            return self._runs.get(run_id)

    def compare_models(self) -> Dict[str, any]:
        """Generate side-by-side comparison across all evaluated models."""
        with self._lock:
            models = list(self._models.values())

        comparison_table = []
        best_accuracy = {"model": None, "val": -1.0}
        best_latency = {"model": None, "val": 999999.0}
        best_cost = {"model": None, "val": 999999.0}

        for m in models:
            metrics = model_adapter.generate_metrics_for_model(m)
            summary = policy_engine.evaluate_model(metrics)

            if metrics.accuracy > best_accuracy["val"]:
                best_accuracy = {"model": m.name, "val": metrics.accuracy}
            if metrics.latency_p95_ms < best_latency["val"]:
                best_latency = {"model": m.name, "val": metrics.latency_p95_ms}
            if metrics.blended_cost_per_1k < best_cost["val"]:
                best_cost = {"model": m.name, "val": metrics.blended_cost_per_1k}

            comparison_table.append({
                "model_id": m.id,
                "model_name": m.name,
                "provider": m.provider,
                "tier": m.tier.value,
                "accuracy": round(metrics.accuracy * 100, 1),
                "latency_p95_ms": metrics.latency_p95_ms,
                "cost_per_1k": round(metrics.blended_cost_per_1k, 4),
                "safety_pass_rate": round(metrics.safety_pass_rate * 100, 1),
                "adversarial_vuln": round(metrics.adversarial_vulnerability_score * 100, 1),
                "pii_leak_rate": round(metrics.pii_leak_rate * 100, 2),
                "policy_status": summary.overall_status.value,
                "summary": summary.summary_message,
            })

        # Recommendation logic: highest accuracy among models that PASS all controls
        recommended = None
        passing_models = [c for c in comparison_table if c["policy_status"] in ("PASS", "EXCEPTION_APPROVED")]
        if passing_models:
            recommended = max(passing_models, key=lambda x: x["accuracy"])["model_name"]

        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "models_evaluated": len(comparison_table),
            "comparison_table": comparison_table,
            "recommended_model": recommended,
            "best_accuracy_model": best_accuracy["model"],
            "best_latency_model": best_latency["model"],
            "best_cost_model": best_cost["model"],
        }


eval_service = EvaluationService()
