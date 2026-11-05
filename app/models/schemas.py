"""API schemas and request/response models."""
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field, field_validator
from app.models.domain import (
    ModelTier,
    UserRole,
    PolicyStatus,
    EvaluationMetrics,
    PolicyEvaluationSummary,
    ExceptionToken,
    AuditRecord,
    EvaluationRun,
)


class ModelRegisterRequest(BaseModel):
    id: str = Field(..., min_length=3, max_length=64, pattern=r"^[a-zA-Z0-9_\-]+$")
    name: str = Field(..., min_length=2, max_length=128)
    provider: str = Field(..., min_length=2, max_length=128)
    tier: ModelTier
    version: str = Field(..., min_length=1, max_length=32)
    context_window: int = Field(default=32768, ge=512, le=2000000)
    cost_per_1k_prompt: float = Field(..., ge=0.0)
    cost_per_1k_completion: float = Field(..., ge=0.0)
    blended_cost_per_1k: float = Field(..., ge=0.0)
    intended_use: str = Field(..., min_length=5, max_length=500)


class RunEvaluationRequest(BaseModel):
    model_id: str
    dataset_name: Optional[str] = "financial-qa-v1.4"
    include_adversarial: bool = True
    include_pii_tests: bool = True
    active_exception_tokens: Optional[List[str]] = Field(default_factory=list)


class ExceptionGrantRequest(BaseModel):
    model_id: str
    rule_id: str
    reason: str = Field(..., min_length=10, max_length=500)
    compensating_control: str = Field(..., min_length=10, max_length=500)
    duration_days: int = Field(default=14, ge=1, le=90)


class PolicyThresholdUpdateRequest(BaseModel):
    rule_id: str
    new_threshold: float
    justification: str = Field(..., min_length=10, max_length=500)


class ModelComparisonResponse(BaseModel):
    timestamp: str
    models_evaluated: int
    comparison_table: List[Dict[str, Any]]
    recommended_model: Optional[str]
    best_cost_model: Optional[str]
    best_latency_model: Optional[str]
    best_accuracy_model: Optional[str]


class SystemHealthResponse(BaseModel):
    status: str
    version: str
    timestamp: str
    environment: str
    dependencies: Dict[str, str]
    audit_chain_healthy: bool
    total_audit_records: int


class AuditVerificationResponse(BaseModel):
    is_valid: bool
    total_records: int
    genesis_hash: str
    latest_hash: str
    broken_link_sequence_id: Optional[int] = None
    verification_message: str
    checked_at: str


class OperationalMetricsResponse(BaseModel):
    policy_coverage_pct: float
    blocked_bypass_attempts: int
    false_positive_rate_pct: float
    audit_completeness_pct: float
    average_evaluation_seconds: float
    manual_review_reduction_pct: float
    estimated_annual_cost_avoidance_usd: float
    baseline_vs_deployed: Dict[str, Any]
