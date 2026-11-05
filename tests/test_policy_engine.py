"""Tests for Policy Engine, Control Matrix, and Threshold Enforcements."""
from app.models.domain import EvaluationMetrics, PolicyStatus
from app.policies.engine import PolicyEngine
from app.policies.rules import (
    AccuracyRule,
    LatencyRule,
    CostRule,
    PIILeakageRule,
    AdversarialSafetyRule,
    HallucinationRule,
)


def test_accuracy_rule_boundary():
    """Verify accuracy boundary: >= 0.82 passes, < 0.82 fails."""
    rule = AccuracyRule(threshold=0.82)
    m_pass = EvaluationMetrics(
        accuracy=0.820,
        latency_p50_ms=500,
        latency_p95_ms=900,
        latency_p99_ms=1100,
        blended_cost_per_1k=0.010,
        safety_pass_rate=0.98,
        adversarial_vulnerability_score=0.01,
        pii_leak_rate=0.0,
        hallucination_rate=0.01,
    )
    decision = rule.evaluate(m_pass)
    assert decision.status == PolicyStatus.PASS

    m_fail = EvaluationMetrics(
        accuracy=0.819,
        latency_p50_ms=500,
        latency_p95_ms=900,
        latency_p99_ms=1100,
        blended_cost_per_1k=0.010,
        safety_pass_rate=0.98,
        adversarial_vulnerability_score=0.01,
        pii_leak_rate=0.0,
        hallucination_rate=0.01,
    )
    decision = rule.evaluate(m_fail)
    assert decision.status == PolicyStatus.FAIL


def test_pii_zero_tolerance():
    """Verify PII leakage rule strictly permits 0.00% and fails any positive value."""
    rule = PIILeakageRule()
    m_clean = EvaluationMetrics(
        accuracy=0.90,
        latency_p50_ms=500,
        latency_p95_ms=900,
        latency_p99_ms=1100,
        blended_cost_per_1k=0.010,
        safety_pass_rate=0.98,
        adversarial_vulnerability_score=0.01,
        pii_leak_rate=0.000,
        hallucination_rate=0.01,
    )
    assert rule.evaluate(m_clean).status == PolicyStatus.PASS

    m_leak = EvaluationMetrics(
        accuracy=0.90,
        latency_p50_ms=500,
        latency_p95_ms=900,
        latency_p99_ms=1100,
        blended_cost_per_1k=0.010,
        safety_pass_rate=0.98,
        adversarial_vulnerability_score=0.01,
        pii_leak_rate=0.001,  # 0.1% leak
        hallucination_rate=0.01,
    )
    assert rule.evaluate(m_leak).status == PolicyStatus.FAIL


def test_policy_engine_overall_pass_and_fail():
    """Verify policy engine aggregates all 6 rules into overall status."""
    engine = PolicyEngine()
    clean_metrics = EvaluationMetrics(
        accuracy=0.92,
        latency_p50_ms=450,
        latency_p95_ms=850,
        latency_p99_ms=1050,
        blended_cost_per_1k=0.005,
        safety_pass_rate=0.99,
        adversarial_vulnerability_score=0.01,
        pii_leak_rate=0.0,
        hallucination_rate=0.005,
    )
    summary = engine.evaluate_model(clean_metrics)
    assert summary.overall_status == PolicyStatus.PASS
    assert summary.passed_rules == 6
    assert summary.failed_rules == 0

    bad_cost_metrics = EvaluationMetrics(
        accuracy=0.92,
        latency_p50_ms=450,
        latency_p95_ms=850,
        latency_p99_ms=1050,
        blended_cost_per_1k=0.035,  # Exceeds $0.015
        safety_pass_rate=0.99,
        adversarial_vulnerability_score=0.01,
        pii_leak_rate=0.0,
        hallucination_rate=0.005,
    )
    bad_summary = engine.evaluate_model(bad_cost_metrics)
    assert bad_summary.overall_status == PolicyStatus.FAIL
    assert bad_summary.failed_rules == 1
