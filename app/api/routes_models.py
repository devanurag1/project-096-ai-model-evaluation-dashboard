"""API routes for model registry management."""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from app.models.domain import ModelCandidate
from app.models.schemas import ModelRegisterRequest
from app.services.eval_service import eval_service
from app.security.auth import AuthenticatedUser
from app.api.dependencies import get_current_user, get_correlation_id, require_permission


router = APIRouter(prefix="/api/models", tags=["Model Registry"])


@router.get("", response_model=List[ModelCandidate])
def list_models(
    user: AuthenticatedUser = Depends(require_permission("models:read")),
):
    """List all candidate models in the evaluation registry."""
    return eval_service.list_models()


@router.get("/{model_id}", response_model=ModelCandidate)
def get_model(
    model_id: str,
    user: AuthenticatedUser = Depends(require_permission("models:read")),
):
    """Get details for a specific model candidate."""
    model = eval_service.get_model(model_id)
    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Model candidate '{model_id}' not found.",
        )
    return model


@router.post("", response_model=ModelCandidate, status_code=status.HTTP_201_CREATED)
def register_model(
    req: ModelRegisterRequest,
    user: AuthenticatedUser = Depends(require_permission("models:register")),
    correlation_id: str = Depends(get_correlation_id),
):
    """Register a new candidate model for evaluation (Requires eval_engineer or higher)."""
    existing = eval_service.get_model(req.id)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Model with ID '{req.id}' is already registered.",
        )

    model = ModelCandidate(
        id=req.id,
        name=req.name,
        provider=req.provider,
        tier=req.tier,
        version=req.version,
        context_window=req.context_window,
        cost_per_1k_prompt=req.cost_per_1k_prompt,
        cost_per_1k_completion=req.cost_per_1k_completion,
        blended_cost_per_1k=req.blended_cost_per_1k,
        intended_use=req.intended_use,
        registered_by=user.email,
    )
    return eval_service.register_model(
        model=model,
        actor=user.email,
        role=user.role.value,
        correlation_id=correlation_id,
    )
