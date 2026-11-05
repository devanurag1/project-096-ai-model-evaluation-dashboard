"""Core domain data models for AI Model Evaluation."""
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field


class PolicyStatus(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    EXCEPTION_REQUIRED = "EXCEPTION_REQUIRED"
    EXCEPTION_APPROVED = "EXCEPTION_APPROVED"


class UserRole(str, Enum):
    BUSINESS_USER = "business_user"
    EVAL_ENGINEER = "eval_engineer"
    COMPLIANCE_OFFICER = "compliance_officer"
    SECOPS_ADMIN = "secops_admin"


class ModelTier(str, Enum):
    FRONTIER_API = "FRONTIER_API"
    SELF_HOSTED_PRIVATE = "SELF_HOSTED_PRIVATE"
    LIGHTWEIGHT_VPC = "LIGHTWEIGHT_VPC"
    LEGACY_DEPRECATED = "LEGACY_DEPRECATED"


class ModelCandidate(BaseModel):
    id: str
    name: str
    provider: str
    tier: ModelTier
    version: str
    context_window: int = 32768
    cost_per_1k_prompt: float
    cost_per_1k_completion: float
    blended_cost_per_1k: float
    intended_use: str
    registered_by: str
    registered_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    status: str = "PENDING_EVAL"


class EvaluationMetrics(BaseModel):
    accuracy: float = Field(..., ge=0.0, le=1.0, description="Task accuracy on financial benchmark suite (0.0 to 1.0)")
    latency_p50_ms: float = Field(..., ge=0.0, description="Median total latency in ms")
    latency_p95_ms: float = Field(..., ge=0.0, description="95th percentile latency in ms")
    latency_p99_ms: float = Field(..., ge=0.0, description="99th percentile latency in ms")
    blended_cost_per_1k: float = Field(..., ge=0.0, description="Blended prompt/completion cost per 1000 tokens in USD")
    safety_pass_rate: float = Field(..., ge=0.0, le=1.0, description="Proportion of safety tests passed safely (0.0 to 1.0)")
    adversarial_vulnerability_score: float = Field(..., ge=0.0, le=1.0, description="Jailbreak & injection vulnerability rate (0.0 to 1.0)")
    pii_leak_rate: float = Field(..., ge=0.0, le=1.0, description="Rate of unredacted PII leakage (strict zero tolerance)")
    hallucination_rate: float = Field(..., ge=0.0, le=1.0, description="Rate of unsubstantiated financial statements (0.0 to 1.0)")
    total_test_items: int = Field(default=0, ge=0)
    total_tokens_evaluated: int = Field(default=0, ge=0)


class PolicyGateDecision(BaseModel):
    rule_id: str
    rule_name: str
    category: str
    status: PolicyStatus
    actual_value: float
    threshold_value: float
    comparator: str
    reason: str
    is_exception_applied: bool = False
    exception_token_id: Optional[str] = None


class PolicyEvaluationSummary(BaseModel):
    overall_status: PolicyStatus
    evaluated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    gate_decisions: List[PolicyGateDecision]
    total_rules: int
    passed_rules: int
    failed_rules: int
    exception_rules: int
    policy_coverage_pct: float = 100.0
    summary_message: str


class ExceptionToken(BaseModel):
    token_id: str
    model_id: str
    rule_id: str
    approver: str
    approver_role: str
    reason: str
    compensating_control: str
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    expires_at: str
    signature: str


class EvaluationRun(BaseModel):
    run_id: str
    model_id: str
    model_name: str
    evaluator: str
    evaluator_role: str
    evaluated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    dataset_version: str = "financial-qa-v1.4"
    dataset_hash: str
    metrics: EvaluationMetrics
    policy_summary: PolicyEvaluationSummary
    applied_exceptions: List[ExceptionToken] = Field(default_factory=list)
    evidence_hash: str
    status: str  # "COMPLETED", "QUARANTINED", "BLOCKED"
    correlation_id: str


class AuditRecord(BaseModel):
    sequence_id: int
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    actor: str
    role: str
    action: str
    resource: str
    result: str  # "ALLOWED", "DENIED", "EXCEPTION_GRANTED", "ALERT"
    reason: str
    correlation_id: str
    payload_hash: str
    prev_hash: str
    hmac_signature: str
    details: Optional[Dict[str, Any]] = None
