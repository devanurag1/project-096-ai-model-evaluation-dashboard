"""Operational, quality, and business impact metrics calculation service."""
import threading
from typing import Dict, Any
from app.audit.ledger import audit_ledger


class MetricsService:
    """Calculates simulated portfolio metrics and business outcomes."""

    def __init__(self):
        self._lock = threading.Lock()
        self._blocked_bypasses: int = 14  # Initial simulated historical bypass attempts blocked
        self._total_evaluated_queries: int = 2480
        self._false_positives: int = 45  # 45 / 2480 = 1.81%

    def record_blocked_bypass(self) -> None:
        """Increment count of blocked bypass attempts."""
        with self._lock:
            self._blocked_bypasses += 1

    def get_operational_metrics(self) -> Dict[str, Any]:
        """Compute system operational metrics comparing manual baseline vs automated deployment."""
        with self._lock:
            blocked_count = self._blocked_bypasses
            fp_rate = round((self._false_positives / self._total_evaluated_queries) * 100, 2)

        total_audit_records = audit_ledger.count()
        # Audit completeness: verifies that 100% of recorded actions have non-empty HMAC and hash links
        is_intact, _, _ = audit_ledger.verify_integrity()
        audit_completeness = 100.0 if is_intact else 0.0

        return {
            "policy_coverage_pct": 100.0,
            "blocked_bypass_attempts": blocked_count,
            "false_positive_rate_pct": fp_rate,
            "audit_completeness_pct": audit_completeness,
            "average_evaluation_seconds": 14.2,
            "manual_review_reduction_pct": 94.5,
            "estimated_annual_cost_avoidance_usd": 142500.0,
            "baseline_vs_deployed": {
                "metric_comparison": [
                    {
                        "metric": "Evaluation Cycle Time",
                        "baseline_manual": "3 to 5 business days per model candidate",
                        "deployed_system": "14.2 seconds automated full-battery sweep",
                        "delta_improvement": "99.8% reduction in latency",
                    },
                    {
                        "metric": "Policy Coverage",
                        "baseline_manual": "Ad-hoc developer checklists (~40% coverage)",
                        "deployed_system": "100.0% systematic Control Matrix enforcement",
                        "delta_improvement": "+60% coverage improvement",
                    },
                    {
                        "metric": "Evidence Auditability",
                        "baseline_manual": "Scattered spreadsheets and Slack messages",
                        "deployed_system": "Cryptographically chained, tamper-evident SHA-256 ledger",
                        "delta_improvement": "Zero repudiation / Instant verification",
                    },
                    {
                        "metric": "Cost per Evaluation",
                        "baseline_manual": "$1,200 (Engineering & Compliance SME hours)",
                        "deployed_system": "$0.08 (Automated API inference cost)",
                        "delta_improvement": "99.9% cost reduction",
                    },
                    {
                        "metric": "Adversarial & PII Detection",
                        "baseline_manual": "Sampled manual inspection (< 5% test vectors)",
                        "deployed_system": "Continuous red-team fixtures & zero-tolerance PII gate",
                        "delta_improvement": "14 blocked adversarial bypass attempts",
                    },
                ],
                "assumptions": (
                    "Simulated portfolio metrics based on mid-size enterprise deploying 12 model evaluations/year "
                    "with 240,000 monthly customer financial advisory queries."
                ),
            },
        }


metrics_service = MetricsService()
