"""API routes for system observability, governance metrics, and business outcomes."""
from fastapi import APIRouter, Depends
from app.models.schemas import OperationalMetricsResponse
from app.services.metrics_service import metrics_service
from app.security.auth import AuthenticatedUser
from app.api.dependencies import require_permission


router = APIRouter(prefix="/api/metrics", tags=["Operational Metrics"])


@router.get("", response_model=OperationalMetricsResponse)
def get_metrics(
    user: AuthenticatedUser = Depends(require_permission("metrics:read")),
):
    """Retrieve system operational metrics, policy coverage, and simulated business ROI."""
    return metrics_service.get_operational_metrics()
