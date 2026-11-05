"""Policy Engine for executing control matrix checks and evaluating exception tokens."""
from datetime import datetime, timezone
from typing import Dict, List, Optional
from app.config import settings
from app.models.domain import (
    EvaluationMetrics,
    PolicyGateDecision,
    PolicyStatus,
    PolicyEvaluationSummary,
    ExceptionToken,
)
from app.policies.rules import (
    BasePolicyRule,
    AccuracyRule,
    LatencyRule,
    CostRule,
    PIILeakageRule,
    AdversarialSafetyRule,
    HallucinationRule,
)
from app.security.tokens import verify_exception_token, ZERO_TOLERANCE_RULES


class PolicyEngine:
    """Enforces enterprise controls over AI model evaluation results."""

    def __init__(self):
        self._rules: Dict[str, BasePolicyRule] = {
            "CTL-ACC-01": AccuracyRule(),
            "CTL-LAT-02": LatencyRule(),
            "CTL-CST-03": CostRule(),
            "CTL-SAF-04": PIILeakageRule(),
            "CTL-SAF-05": AdversarialSafetyRule(),
            "CTL-SAF-06": HallucinationRule(),
        }

    def list_rules(self) -> List[Dict[str, any]]:
        """List active rules and their configured thresholds."""
        rule_list = []
        for r_id, r in self._rules.items():
            threshold_val = getattr(r, "threshold", getattr(r, "max_p95_ms", getattr(r, "max_cost_usd", getattr(r, "max_vulnerability", getattr(r, "max_rate", getattr(r, "max_leak_rate", 0.0))))))
            rule_list.append({
                "rule_id": r.rule_id,
                "rule_name": r.rule_name,
                "category": r.category,
                "comparator": r.comparator,
                "threshold": threshold_val,
                "allows_exceptions": r.allows_exceptions,
            })
        return rule_list

    def update_threshold(self, rule_id: str, new_threshold: float) -> bool:
        """Update a rule threshold dynamically."""
        if rule_id not in self._rules:
            return False

        rule = self._rules[rule_id]
        if rule_id == "CTL-SAF-04":
            raise ValueError("CTL-SAF-04 is a zero-tolerance control and threshold cannot be modified.")

        if isinstance(rule, AccuracyRule):
            rule.threshold = new_threshold
        elif isinstance(rule, LatencyRule):
            rule.max_p95_ms = new_threshold
        elif isinstance(rule, CostRule):
            rule.max_cost_usd = new_threshold
        elif isinstance(rule, AdversarialSafetyRule):
            rule.max_vulnerability = new_threshold
        elif isinstance(rule, HallucinationRule):
            rule.max_rate = new_threshold
        return True

    def evaluate_model(
        self,
        metrics: EvaluationMetrics,
        exception_tokens: Optional[List[ExceptionToken]] = None,
    ) -> PolicyEvaluationSummary:
        """
        Evaluate metrics against all active controls with fail-closed semantics.
        Verifies cryptographic exception tokens for non-zero-tolerance failures.
        """
        exception_map: Dict[str, ExceptionToken] = {}
        if exception_tokens:
            for tok in exception_tokens:
                exception_map[tok.rule_id] = tok

        gate_decisions: List[PolicyGateDecision] = []
        passed_count = 0
        failed_count = 0
        exception_count = 0

        # Evaluate each control deterministically
        for rule_id, rule in self._rules.items():
            try:
                decision = rule.evaluate(metrics)
            except Exception as e:
                # FAIL-CLOSED: Any evaluation failure defaults to FAIL
                decision = PolicyGateDecision(
                    rule_id=rule_id,
                    rule_name=rule.rule_name,
                    category=rule.category,
                    status=PolicyStatus.FAIL,
                    actual_value=0.0,
                    threshold_value=0.0,
                    comparator=rule.comparator,
                    reason=f"Policy evaluation exception occurred: {str(e)}",
                )

            # Check if an exception token exists for this rule
            if decision.status == PolicyStatus.FAIL and rule_id in exception_map:
                token = exception_map[rule_id]
                is_valid, reason = verify_exception_token(token)
                if is_valid:
                    decision.status = PolicyStatus.EXCEPTION_APPROVED
                    decision.is_exception_applied = True
                    decision.exception_token_id = token.token_id
                    decision.reason += f" [EXCEPTION GRANTED by {token.approver}: {token.reason}]"
                    exception_count += 1
                else:
                    # Token invalid / expired / zero-tolerance attempt -> Fail closed
                    decision.reason += f" [EXCEPTION REJECTED: {reason}]"
                    failed_count += 1
            elif decision.status == PolicyStatus.FAIL:
                failed_count += 1
            else:
                passed_count += 1

            gate_decisions.append(decision)

        # Overall Status Calculation
        if failed_count > 0:
            overall_status = PolicyStatus.FAIL
            summary_msg = f"Model rejected: {failed_count} policy gate(s) failed."
        elif exception_count > 0:
            overall_status = PolicyStatus.EXCEPTION_APPROVED
            summary_msg = f"Model conditionally approved: {exception_count} policy exception(s) verified cryptographically."
        else:
            overall_status = PolicyStatus.PASS
            summary_msg = f"Model fully approved: All {passed_count} policy gates passed."

        return PolicyEvaluationSummary(
            overall_status=overall_status,
            evaluated_at=datetime.now(timezone.utc).isoformat(),
            gate_decisions=gate_decisions,
            total_rules=len(self._rules),
            passed_rules=passed_count,
            failed_rules=failed_count,
            exception_rules=exception_count,
            policy_coverage_pct=100.0,
            summary_message=summary_msg,
        )


policy_engine = PolicyEngine()
