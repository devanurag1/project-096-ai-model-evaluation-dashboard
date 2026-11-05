"""API routes for model evaluation runs and comparative analysis."""
import json
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from app.config import settings
from app.models.domain import EvaluationRun
from app.models.schemas import RunEvaluationRequest, ModelComparisonResponse
from app.services.eval_service import eval_service
from app.security.auth import AuthenticatedUser
from app.api.dependencies import get_current_user, get_correlation_id, require_permission


router = APIRouter(prefix="/api/eval", tags=["Evaluation Workflow"])


@router.post("/run", response_model=EvaluationRun)
def trigger_evaluation(
    req: RunEvaluationRequest,
    user: AuthenticatedUser = Depends(require_permission("evaluations:run")),
    correlation_id: str = Depends(get_correlation_id),
):
    """Trigger a full evaluation sweep across Accuracy, Latency, Cost, and Safety controls."""
    try:
        run = eval_service.run_evaluation(
            model_id=req.model_id,
            evaluator_id=user.email,
            evaluator_role=user.role.value,
            correlation_id=correlation_id,
            active_exception_tokens=req.active_exception_tokens,
        )
        return run
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Evaluation failed safely: {str(e)}",
        )


@router.get("/runs", response_model=List[EvaluationRun])
def list_evaluation_runs(
    user: AuthenticatedUser = Depends(require_permission("evaluations:read")),
):
    """List historical evaluation runs and gate decisions."""
    return eval_service.list_runs()


@router.get("/runs/{run_id}", response_model=EvaluationRun)
def get_evaluation_run(
    run_id: str,
    user: AuthenticatedUser = Depends(require_permission("evaluations:read")),
):
    """Get single evaluation run including evidence hash and policy breakdown."""
    run = eval_service.get_run(run_id)
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Evaluation run '{run_id}' not found.",
        )
    return run


@router.get("/compare", response_model=ModelComparisonResponse)
def compare_models(
    user: AuthenticatedUser = Depends(require_permission("comparison:read")),
):
    """Generate comparative matrix across Accuracy, Latency, Cost, and Safety."""
    return eval_service.compare_models()


@router.get("/fixtures/benchmark")
def get_benchmark_fixtures(
    user: AuthenticatedUser = Depends(require_permission("benchmarks:read")),
):
    """View the financial domain QA benchmark fixture items."""
    fixture_path = settings.FIXTURES_DIR / "benchmark_dataset.json"
    if not fixture_path.exists():
        return []
    with open(fixture_path, "r", encoding="utf-8") as f:
        return json.load(f)


@router.get("/fixtures/adversarial")
def get_adversarial_fixtures(
    user: AuthenticatedUser = Depends(require_permission("benchmarks:read")),
):
    """View the adversarial red-teaming and jailbreak fixture items."""
    fixture_path = settings.FIXTURES_DIR / "adversarial_prompts.json"
    if not fixture_path.exists():
        return []
    with open(fixture_path, "r", encoding="utf-8") as f:
        return json.load(f)
